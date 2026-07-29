import CoreML
import Foundation

struct HeadFixture: Decodable {
    let name: String
    let inputMode: String
    let famEnabled: Bool
    let headMode: String
    let routerOverrideApplied: Bool
    let batchSize: Int
    let inputShape: [Int]
    let outputShape: [Int]
    let features: [Float]
    let expectedLogits: [Float]
    let expectedTopK: [Int]

    enum CodingKeys: String, CodingKey {
        case name
        case inputMode = "input_mode"
        case famEnabled = "fam_enabled"
        case headMode = "head_mode"
        case routerOverrideApplied = "router_override_applied"
        case batchSize = "batch_size"
        case inputShape = "input_shape"
        case outputShape = "output_shape"
        case features
        case expectedLogits = "expected_logits"
        case expectedTopK = "expected_topk"
    }
}

struct HeadResult: Encodable {
    let modelName: String
    let headMode: String
    let famEnabled: Bool
    let inputMode: String
    let computeUnits: String
    let routerOverrideApplied: Bool
    let inferenceCount: Int
    let latencyMs: Double
    let inputAllZero: Bool
    let actualOutputShape: [Int]
    let expectedOutputShape: [Int]
    let outputShapeMatches: Bool
    let logitsFinite: Bool
    let deterministicRepeatMatch: Bool
    let repeatMaxAbsError: Double?
    let maxAbsError: Double?
    let actualLogits: [Double]
    let expectedLogits: [Double]
    let actualTopK: [Int]
    let expectedTopK: [Int]
    let topKMatch: Bool
    let passed: Bool

    enum CodingKeys: String, CodingKey {
        case modelName = "model_name"
        case headMode = "head_mode"
        case famEnabled = "fam_enabled"
        case inputMode = "input_mode"
        case computeUnits = "compute_units"
        case routerOverrideApplied = "router_override_applied"
        case inferenceCount = "inference_count"
        case latencyMs = "latency_ms"
        case inputAllZero = "input_all_zero"
        case actualOutputShape = "actual_output_shape"
        case expectedOutputShape = "expected_output_shape"
        case outputShapeMatches = "output_shape_matches"
        case logitsFinite = "logits_finite"
        case deterministicRepeatMatch = "deterministic_repeat_match"
        case repeatMaxAbsError = "repeat_max_abs_error"
        case maxAbsError = "max_abs_error"
        case actualLogits = "actual_logits"
        case expectedLogits = "expected_logits"
        case actualTopK = "actual_top_k"
        case expectedTopK = "expected_top_k"
        case topKMatch = "top_k_match"
        case passed
    }
}

struct Arguments {
    var model = ""
    var fixture = ""
    var jsonOutput = ""

    static func parse() throws -> Arguments {
        var result = Arguments()
        var index = 1
        let arguments = CommandLine.arguments
        while index < arguments.count {
            guard index + 1 < arguments.count else {
                throw NSError(domain: "MoeHeadBaseline", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "option値が不足しています: \(arguments[index])"
                ])
            }
            let value = arguments[index + 1]
            switch arguments[index] {
            case "--model": result.model = value
            case "--fixture": result.fixture = value
            case "--json-output": result.jsonOutput = value
            default:
                throw NSError(domain: "MoeHeadBaseline", code: 2, userInfo: [
                    NSLocalizedDescriptionKey: "未対応optionです: \(arguments[index])"
                ])
            }
            index += 2
        }
        guard !result.model.isEmpty, !result.fixture.isEmpty, !result.jsonOutput.isEmpty else {
            throw NSError(domain: "MoeHeadBaseline", code: 2, userInfo: [
                NSLocalizedDescriptionKey: "--model、--fixture、--json-outputは必須です"
            ])
        }
        return result
    }
}

func stableTopK(
    logits: [Double], batchSize: Int, outputDimension: Int, k: Int = 2
) -> [Int] {
    guard batchSize > 0, outputDimension > 0, logits.count == batchSize * outputDimension else {
        return []
    }
    var result: [Int] = []
    for batch in 0..<batchSize {
        let offset = batch * outputDimension
        let indices = Array(0..<outputDimension).sorted { left, right in
            let leftScore = logits[offset + left]
            let rightScore = logits[offset + right]
            if leftScore == rightScore { return left < right }
            return leftScore > rightScore
        }
        result.append(contentsOf: indices.prefix(min(k, outputDimension)))
    }
    return result
}

func modelOutput(
    _ model: MLModel, provider: MLFeatureProvider
) throws -> (values: [Double], shape: [Int]) {
    let prediction = try model.prediction(from: provider)
    guard let output = prediction.featureValue(for: "priority_logits")?.multiArrayValue else {
        throw NSError(domain: "MoeHeadBaseline", code: 4, userInfo: [
            NSLocalizedDescriptionKey: "priority_logits出力がありません"
        ])
    }
    return (
        values: (0..<output.count).map { output[$0].doubleValue },
        shape: output.shape.map { $0.intValue }
    )
}

func maximumAbsoluteError(_ left: [Double], _ right: [Double]) -> Double? {
    guard
        left.count == right.count,
        !left.isEmpty,
        left.allSatisfy({ $0.isFinite }),
        right.allSatisfy({ $0.isFinite })
    else { return nil }
    return zip(left, right).map { pair in abs(pair.0 - pair.1) }.max()
}

func validateFixtureSchema(_ fixture: HeadFixture) throws {
    let inputDimension = 16
    let outputDimension = 4
    let topK = 2
    guard fixture.batchSize > 0 else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "batch sizeは正数でなければなりません"
        ])
    }
    guard fixture.inputShape == [fixture.batchSize, inputDimension] else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "input shapeは[batch, 16]でなければなりません"
        ])
    }
    guard fixture.outputShape == [fixture.batchSize, outputDimension] else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "output shapeは[batch, 4]でなければなりません"
        ])
    }
    guard
        fixture.features.count == fixture.batchSize * inputDimension,
        fixture.expectedLogits.count == fixture.batchSize * outputDimension,
        fixture.expectedTopK.count == fixture.batchSize * topK
    else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "fixture tensorの要素数がshapeと一致しません"
        ])
    }
    for batch in 0..<fixture.batchSize {
        let row = Array(fixture.expectedTopK[(batch * topK)..<((batch + 1) * topK)])
        guard Set(row).count == topK, row.allSatisfy({ (0..<outputDimension).contains($0) }) else {
            throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
                NSLocalizedDescriptionKey: "expected top-kに重複または範囲外indexがあります"
            ])
        }
    }
    let expectedTopKFromLogits = stableTopK(
        logits: fixture.expectedLogits.map(Double.init),
        batchSize: fixture.batchSize,
        outputDimension: outputDimension,
        k: topK
    )
    guard expectedTopKFromLogits == fixture.expectedTopK else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "expected logitsとexpected top-kが一致しません"
        ])
    }
}

func run() throws {
    let arguments = try Arguments.parse()
    let fixtureData = try Data(contentsOf: URL(fileURLWithPath: arguments.fixture))
    let fixture = try JSONDecoder().decode(HeadFixture.self, from: fixtureData)
    try validateFixtureSchema(fixture)

    guard fixture.headMode == "observe_only" else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "HEAD modeがobserve_onlyではありません"
        ])
    }
    guard !fixture.famEnabled, !fixture.routerOverrideApplied else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "FAMまたはrouter overrideが有効なfixtureは拒否します"
        ])
    }
    guard fixture.inputMode == "zero", fixture.features.allSatisfy({ $0 == 0 }) else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "FAM未接続baselineはzero inputだけを受け付けます"
        ])
    }

    let input = try MLMultiArray(
        shape: fixture.inputShape.map { NSNumber(value: $0) }, dataType: .float32
    )
    guard input.count == fixture.features.count else {
        throw NSError(domain: "MoeHeadBaseline", code: 3, userInfo: [
            NSLocalizedDescriptionKey: "fixture input shapeとfeature数が一致しません"
        ])
    }
    for (index, value) in fixture.features.enumerated() {
        input[index] = NSNumber(value: value)
    }
    let provider = try MLDictionaryFeatureProvider(dictionary: [
        "features": MLFeatureValue(multiArray: input)
    ])
    let configuration = MLModelConfiguration()
    configuration.computeUnits = .cpuOnly
    let model = try MLModel(
        contentsOf: URL(fileURLWithPath: arguments.model), configuration: configuration
    )

    let started = DispatchTime.now().uptimeNanoseconds
    let first = try modelOutput(model, provider: provider)
    let second = try modelOutput(model, provider: provider)
    let finished = DispatchTime.now().uptimeNanoseconds

    let expected = fixture.expectedLogits.map(Double.init)
    let outputDimension = fixture.outputShape.last ?? 0
    let actualTopK = stableTopK(
        logits: second.values,
        batchSize: fixture.batchSize,
        outputDimension: outputDimension
    )
    let repeatError = maximumAbsoluteError(first.values, second.values)
    let referenceError = maximumAbsoluteError(second.values, expected)
    let outputShapeMatches = second.shape == fixture.outputShape
    let logitsFinite = second.values.allSatisfy { $0.isFinite }
    let deterministicRepeatMatch = repeatError.map { $0 <= 1e-7 } ?? false
    let topKMatch = actualTopK == fixture.expectedTopK
    let passed = (
        !fixture.famEnabled
        && !fixture.routerOverrideApplied
        && fixture.inputMode == "zero"
        && fixture.features.allSatisfy { $0 == 0 }
        && outputShapeMatches
        && logitsFinite
        && deterministicRepeatMatch
        && (referenceError.map { $0 <= 1e-5 } ?? false)
        && topKMatch
    )
    let report = HeadResult(
        modelName: fixture.name,
        headMode: fixture.headMode,
        famEnabled: fixture.famEnabled,
        inputMode: fixture.inputMode,
        computeUnits: "cpuOnly",
        routerOverrideApplied: false,
        inferenceCount: 2,
        latencyMs: Double(finished - started) / 1_000_000.0,
        inputAllZero: fixture.features.allSatisfy { $0 == 0 },
        actualOutputShape: second.shape,
        expectedOutputShape: fixture.outputShape,
        outputShapeMatches: outputShapeMatches,
        logitsFinite: logitsFinite,
        deterministicRepeatMatch: deterministicRepeatMatch,
        repeatMaxAbsError: repeatError,
        maxAbsError: referenceError,
        actualLogits: second.values,
        expectedLogits: expected,
        actualTopK: actualTopK,
        expectedTopK: fixture.expectedTopK,
        topKMatch: topKMatch,
        passed: passed
    )
    let encoder = JSONEncoder()
    encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
    encoder.nonConformingFloatEncodingStrategy = .convertToString(
        positiveInfinity: "Infinity", negativeInfinity: "-Infinity", nan: "NaN"
    )
    let data = try encoder.encode(report)
    try data.write(to: URL(fileURLWithPath: arguments.jsonOutput), options: .atomic)
    print(String(data: data, encoding: .utf8) ?? "")
    if !passed { exit(1) }
}

do {
    try run()
} catch {
    fputs("moe-head-baseline: \(error)\n", stderr)
    exit(1)
}
