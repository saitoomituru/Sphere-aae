import Accelerate
import CoreML
import Foundation
import Metal
import MetalPerformanceShaders

struct Fixture: Decodable {
    let name: String
    let batchSize: Int
    let inputShape: [Int]
    let outputShape: [Int]
    let features: [Float]
    let expectedLogits: [Float]

    enum CodingKeys: String, CodingKey {
        case name
        case batchSize = "batch_size"
        case inputShape = "input_shape"
        case outputShape = "output_shape"
        case features
        case expectedLogits = "expected_logits"
    }
}

struct ResultReport: Encodable {
    let profile: String
    let computeUnits: String
    let batchSize: Int
    let warmup: Int
    let iterations: Int
    let maxAbsError: Double
    let p50Ms: Double
    let p95Ms: Double
    let p99Ms: Double
    let acceleratedDevice: String?
    let metal3: Bool
    let mpsSupported: Bool
    let mpsMaxAbsError: Double
    let acceleratePassed: Bool
    let computeDevices: [String]
    let passed: Bool

    enum CodingKeys: String, CodingKey {
        case profile
        case computeUnits = "compute_units"
        case batchSize = "batch_size"
        case warmup
        case iterations
        case maxAbsError = "max_abs_error"
        case p50Ms = "p50_ms"
        case p95Ms = "p95_ms"
        case p99Ms = "p99_ms"
        case acceleratedDevice = "accelerated_device"
        case metal3
        case mpsSupported = "mps_supported"
        case mpsMaxAbsError = "mps_max_abs_error"
        case acceleratePassed = "accelerate_passed"
        case computeDevices = "compute_devices"
        case passed
    }
}

struct Arguments {
    var model = ""
    var fixture = ""
    var profile = "smoke"
    var computeUnits = "cpuOnly"
    var warmup = 20
    var iterations = 100
    var jsonOutput = ""

    static func parse() throws -> Arguments {
        var result = Arguments()
        var index = 1
        let args = CommandLine.arguments
        while index < args.count {
            guard index + 1 < args.count else {
                throw NSError(domain: "CoreMLSmoke", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "Missing value for \(args[index])"
                ])
            }
            let value = args[index + 1]
            switch args[index] {
            case "--model": result.model = value
            case "--fixture": result.fixture = value
            case "--profile": result.profile = value
            case "--compute-units": result.computeUnits = value
            case "--warmup": result.warmup = Int(value) ?? result.warmup
            case "--iterations": result.iterations = Int(value) ?? result.iterations
            case "--json-output": result.jsonOutput = value
            default:
                throw NSError(domain: "CoreMLSmoke", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "Unknown argument: \(args[index])"
                ])
            }
            index += 2
        }
        guard !result.model.isEmpty, !result.fixture.isEmpty, !result.jsonOutput.isEmpty else {
            throw NSError(domain: "CoreMLSmoke", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "--model, --fixture, and --json-output are required"
            ])
        }
        return result
    }
}

func percentile(_ sorted: [Double], _ fraction: Double) -> Double {
    guard !sorted.isEmpty else { return 0 }
    let index = min(sorted.count - 1, Int(Double(sorted.count - 1) * fraction))
    return sorted[index]
}

func coreMLComputeUnits(_ value: String) throws -> MLComputeUnits {
    switch value {
    case "cpuOnly": return .cpuOnly
    case "cpuAndGPU": return .cpuAndGPU
    case "all": return .all
    default:
        throw NSError(domain: "CoreMLSmoke", code: 2, userInfo: [
            NSLocalizedDescriptionKey: "Unknown compute unit mode: \(value)"
        ])
    }
}

func runAccelerateProbe() -> Bool {
    let input: [Float] = [1, 2, 3, 4]
    var output = [Float](repeating: 0, count: input.count)
    vDSP_vsq(input, 1, &output, 1, vDSP_Length(input.count))
    return output == [1, 4, 9, 16]
}

func runMPSProbe(device: MTLDevice) throws -> Double {
    let size = 32
    let rowBytes = MPSMatrixDescriptor.rowBytes(fromColumns: size, dataType: .float32)
    let byteCount = rowBytes * size
    guard
        let leftBuffer = device.makeBuffer(length: byteCount, options: .storageModeShared),
        let rightBuffer = device.makeBuffer(length: byteCount, options: .storageModeShared),
        let resultBuffer = device.makeBuffer(length: byteCount, options: .storageModeShared),
        let queue = device.makeCommandQueue(),
        let commandBuffer = queue.makeCommandBuffer()
    else {
        throw NSError(domain: "CoreMLSmoke", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "Unable to allocate MPS resources"
        ])
    }

    memset(leftBuffer.contents(), 0, byteCount)
    memset(rightBuffer.contents(), 0, byteCount)
    memset(resultBuffer.contents(), 0, byteCount)
    for row in 0..<size {
        let leftRow = leftBuffer.contents().advanced(by: row * rowBytes).bindMemory(
            to: Float.self, capacity: size
        )
        let rightRow = rightBuffer.contents().advanced(by: row * rowBytes).bindMemory(
            to: Float.self, capacity: size
        )
        for column in 0..<size {
            leftRow[column] = Float((row + column) % 7) / 7.0
            rightRow[column] = row == column ? 1.0 : 0.0
        }
    }

    let descriptor = MPSMatrixDescriptor(
        rows: size, columns: size, rowBytes: rowBytes, dataType: .float32
    )
    let left = MPSMatrix(buffer: leftBuffer, descriptor: descriptor)
    let right = MPSMatrix(buffer: rightBuffer, descriptor: descriptor)
    let output = MPSMatrix(buffer: resultBuffer, descriptor: descriptor)
    let multiplication = MPSMatrixMultiplication(
        device: device, resultRows: size, resultColumns: size, interiorColumns: size
    )
    multiplication.encode(
        commandBuffer: commandBuffer,
        leftMatrix: left,
        rightMatrix: right,
        resultMatrix: output
    )
    commandBuffer.commit()
    commandBuffer.waitUntilCompleted()
    if let error = commandBuffer.error { throw error }

    var maxError = 0.0
    for row in 0..<size {
        let leftRow = leftBuffer.contents().advanced(by: row * rowBytes).bindMemory(
            to: Float.self, capacity: size
        )
        let outputRow = resultBuffer.contents().advanced(by: row * rowBytes).bindMemory(
            to: Float.self, capacity: size
        )
        for column in 0..<size {
            maxError = max(maxError, abs(Double(leftRow[column] - outputRow[column])))
        }
    }
    return maxError
}

func run() throws {
    let args = try Arguments.parse()
    let fixtureData = try Data(contentsOf: URL(fileURLWithPath: args.fixture))
    let fixture = try JSONDecoder().decode(Fixture.self, from: fixtureData)
    let input = try MLMultiArray(
        shape: fixture.inputShape.map { NSNumber(value: $0) }, dataType: .float32
    )
    for (index, value) in fixture.features.enumerated() {
        input[index] = NSNumber(value: value)
    }
    let provider = try MLDictionaryFeatureProvider(dictionary: [
        "features": MLFeatureValue(multiArray: input)
    ])

    let configuration = MLModelConfiguration()
    configuration.computeUnits = try coreMLComputeUnits(args.computeUnits)
    let model = try MLModel(contentsOf: URL(fileURLWithPath: args.model), configuration: configuration)

    var firstOutput: MLMultiArray?
    for _ in 0..<args.warmup {
        let prediction = try model.prediction(from: provider)
        firstOutput = prediction.featureValue(for: "priority_logits")?.multiArrayValue
    }
    guard let output = firstOutput else {
        throw NSError(domain: "CoreMLSmoke", code: 4, userInfo: [
            NSLocalizedDescriptionKey: "priority_logits output missing"
        ])
    }

    var maxAbsError = 0.0
    for index in 0..<fixture.expectedLogits.count {
        maxAbsError = max(
            maxAbsError,
            abs(output[index].doubleValue - Double(fixture.expectedLogits[index]))
        )
    }

    var timings = [Double]()
    timings.reserveCapacity(args.iterations)
    for _ in 0..<args.iterations {
        let start = DispatchTime.now().uptimeNanoseconds
        _ = try model.prediction(from: provider)
        let end = DispatchTime.now().uptimeNanoseconds
        timings.append(Double(end - start) / 1_000_000.0)
    }
    timings.sort()

    let device = MTLCopyAllDevices().first
    let mpsSupported = device.map { MPSSupportsMTLDevice($0) } ?? false
    let mpsError = try device.map { try runMPSProbe(device: $0) } ?? .infinity
    let metal3 = device?.supportsFamily(.metal3) ?? false
    let computeDevices: [String]
    if #available(macOS 14.0, *) {
        computeDevices = MLModel.availableComputeDevices.map { String(describing: $0) }
    } else {
        computeDevices = []
    }
    let acceleratePassed = runAccelerateProbe()
    let passed = maxAbsError <= 1e-5 && mpsError <= 1e-6 && acceleratePassed
    let report = ResultReport(
        profile: args.profile,
        computeUnits: args.computeUnits,
        batchSize: fixture.batchSize,
        warmup: args.warmup,
        iterations: args.iterations,
        maxAbsError: maxAbsError,
        p50Ms: percentile(timings, 0.50),
        p95Ms: percentile(timings, 0.95),
        p99Ms: percentile(timings, 0.99),
        acceleratedDevice: device?.name,
        metal3: metal3,
        mpsSupported: mpsSupported,
        mpsMaxAbsError: mpsError,
        acceleratePassed: acceleratePassed,
        computeDevices: computeDevices,
        passed: passed
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    let data = try encoder.encode(report)
    try data.write(to: URL(fileURLWithPath: args.jsonOutput), options: .atomic)
    print(String(data: data, encoding: .utf8) ?? "")
    if !passed { exit(1) }
}

do {
    try run()
} catch {
    fputs("coreml-smoke: \(error)\n", stderr)
    exit(1)
}
