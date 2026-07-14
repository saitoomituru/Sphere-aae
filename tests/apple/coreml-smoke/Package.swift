// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "coreml-smoke",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "coreml-smoke", targets: ["CoreMLSmoke"]),
    ],
    targets: [
        .executableTarget(
            name: "CoreMLSmoke",
            linkerSettings: [
                .linkedFramework("Accelerate"),
                .linkedFramework("CoreML"),
                .linkedFramework("Metal"),
                .linkedFramework("MetalPerformanceShaders"),
            ]
        ),
    ]
)
