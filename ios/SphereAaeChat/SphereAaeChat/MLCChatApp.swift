//
//  SphereAaeChatApp.swift
//  SphereAaeChat
//
//  Created by Tianqi Chen on 4/26/23.
//

import SwiftUI

@main
struct SphereAaeChatApp: App {
    @StateObject private var appState = AppState()

    init() {
        UITableView.appearance().separatorStyle = .none
        UITableView.appearance().tableFooterView = UIView()
    }

    var body: some Scene {
        WindowGroup {
            StartView()
                .environmentObject(appState)
                .task {
                    appState.loadAppConfigAndModels()
                }
        }
    }
}
