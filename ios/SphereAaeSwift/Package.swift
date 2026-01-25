// swift-tools-version:5.5
// The swift-tools-version declares the minimum version of Swift required to build this package.

import PackageDescription

let package = Package(
    name: "SphereAaeSwift",
    products: [
        .library(
            name: "SphereAaeSwift",
            targets: ["SphereAaeEngineObjC", "SphereAaeSwift"]
        )
    ],
    dependencies: [],
    targets: [
        .target(
            name: "SphereAaeEngineObjC",
            path: "Sources/ObjC",
            cxxSettings: [
                .headerSearchPath("../../tvm_home/include"),
                .headerSearchPath("../../tvm_home/3rdparty/tvm-ffi/include"),
                .headerSearchPath("../../tvm_home/3rdparty/tvm-ffi/3rdparty/dlpack/include"),
                .headerSearchPath("../../tvm_home/3rdparty/dmlc-core/include")
            ]
        ),
        .target(
            name: "SphereAaeSwift",
            dependencies: ["SphereAaeEngineObjC"],
            path: "Sources/Swift"
        )
    ],
    cxxLanguageStandard: .cxx17
)
