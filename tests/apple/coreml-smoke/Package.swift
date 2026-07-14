// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "coreml-smoke",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "coreml-smoke", targets: ["CoreMLSmoke"]),
        .executable(name: "moe-head-baseline", targets: ["MoeHeadBaseline"]),
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
        .executableTarget(
            name: "MoeHeadBaseline",
            linkerSettings: [
                .linkedFramework("CoreML"),
            ]
        ),
    ]
)
