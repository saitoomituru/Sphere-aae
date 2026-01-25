//
//  ParamsConfig.swift
//  SphereAaeChat
//

struct ParamsConfig: Decodable {
    struct ParamsRecord: Decodable {
        let dataPath: String
    }

    let records: [ParamsRecord]
}
