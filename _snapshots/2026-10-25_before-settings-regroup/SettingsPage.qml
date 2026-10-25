import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Dialogs
import QtQuick.Layouts

Flickable {
    id: page
    signal toastRequest(string message)
    readonly property var s: backend.settings

    contentHeight: column.implicitHeight + 2 * Theme.s5
    clip: true
    boundsBehavior: Flickable.StopAtBounds
    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

    Loader {
        id: folderLoader
        active: !backend.isMobile
        sourceComponent: FolderDialog {
            title: qsTr("Choose download folder")
            onAccepted: {
                var err = backend.setDownloadDir(selectedFolder.toString())
                if (err) page.toastRequest(err)
            }
        }
    }
    Loader {
        id: ffmpegLoader
        active: !backend.isMobile
        sourceComponent: FileDialog {
            title: qsTr("Choose ffmpeg")
            nameFilters: [qsTr("ffmpeg executable (ffmpeg.exe)"), qsTr("All files (*)")]
            onAccepted: {
                var err = backend.setHelperPath("ffmpeg", selectedFile.toString())
                page.toastRequest(err || qsTr("ffmpeg path saved"))
            }
        }
    }
    Loader {
        id: nodeLoader
        active: !backend.isMobile
        sourceComponent: FileDialog {
            title: qsTr("Choose Node.js")
            nameFilters: [qsTr("Node.js executable (node.exe)"), qsTr("All files (*)")]
            onAccepted: {
                var err = backend.setHelperPath("node", selectedFile.toString())
                page.toastRequest(err || qsTr("Node.js path saved"))
            }
        }
    }

    Loader {
        id: tiddlLoader
        active: !backend.isMobile
        sourceComponent: FileDialog {
            title: qsTr("Choose tiddl")
            nameFilters: [qsTr("tiddl executable (tiddl.exe)"), qsTr("All files (*)")]
            onAccepted: {
                var err = backend.setTidalPath(selectedFile.toString())
                page.toastRequest(err || qsTr("tiddl path saved"))
            }
        }
    }

    ColumnLayout {
        id: column
        x: Theme.compact ? Theme.s4 : Theme.s6
        y: Theme.compact ? Theme.s4 : Theme.s5
        width: Math.min(720, page.width - 2 * (Theme.compact ? Theme.s4 : Theme.s6))
        spacing: Theme.s5

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.s2
            Text {
                text: qsTr("Settings")
                font.pixelSize: Theme.compact ? Theme.title : Theme.largeTitle
                font.weight: Font.DemiBold
                color: Theme.text
                Layout.fillWidth: true
                Accessible.role: Accessible.Heading
            }
            Badge {
                visible: !Theme.compact
                text: backend.settingsDirty ? qsTr("Unsaved changes") : qsTr("No changes")
                kind: backend.settingsDirty ? "warning" : "success"
            }
            AppButton {
                visible: backend.settingsDirty
                text: qsTr("Discard")
                kind: "plain"
                onClicked: { backend.finishSettingsEdit(false); backend.beginSettingsEdit() }
            }
            AppButton {
                text: qsTr("Save")
                iconName: "check"
                kind: "primary"
                enabled: backend.settingsDirty
                onClicked: { backend.commitSettingsEdit(); page.toastRequest(qsTr("Settings saved")) }
            }
        }

        SettingsGroup {
            title: qsTr("Browser")
            icon: "globe"
            collapsible: true
            visible: backend.browserAvailable
            Layout.fillWidth: true
            SettingsItem {
                label: qsTr("YouTube browser on the Downloads page")
                icon: "window"
                summary: page.s.show_browser ? qsTr("On") : qsTr("Off")
                hint: qsTr("Uses the Microsoft Edge WebView2 of Windows. Opening a video fills the link field.")
                stacked: false
                AppSwitch { checked: page.s.show_browser; onToggled: backend.setSetting("show_browser", checked) }
            }
            SettingsItem {
                label: qsTr("Block ads and trackers in the browser (experimental)")
                icon: "block"
                summary: page.s.adblock_experimental ? qsTr("On") : qsTr("Off")
                hint: qsTr("Refuses known ad and tracker domains (own list: blocklist.txt in the Yeal data folder, hosts format). Video ads from YouTube itself are skipped by a script. Off by default. If YouTube misbehaves, leave it off. Takes effect after a restart.")
                stacked: false
                AppSwitch { checked: page.s.adblock_experimental; onToggled: backend.setSetting("adblock_experimental", checked) }
            }
        }

        SettingsGroup {
            title: qsTr("Appearance")
            icon: "sun"
            collapsible: true
            Layout.fillWidth: true
            SettingsItem {
                label: qsTr("Theme")
                icon: "sun"
                summary: page.s.theme === "dark" ? qsTr("Dark") : page.s.theme === "light" ? qsTr("Light") : qsTr("System")
                Segmented {
                    current: page.s.theme
                    options: [{ text: qsTr("System"), value: "system" }, { text: qsTr("Light"), value: "light" },
                              { text: qsTr("Dark"), value: "dark" }]
                    Layout.fillWidth: Theme.compact
                    Layout.preferredWidth: 260
                    onActivated: (v) => backend.setSetting("theme", v)
                }
            }
        }

        SettingsGroup {
            title: qsTr("Downloads")
            icon: "download"
            collapsible: true
            Layout.fillWidth: true
            SettingsItem {
                label: qsTr("Save to")
                icon: "folder"
                summary: page.s.download_dir
                hint: page.s.download_dir
                stacked: Theme.compact
                AppButton { visible: !backend.isMobile; text: qsTr("Choose…"); iconName: "folder"
                            onClicked: folderLoader.item.open() }
                AppButton { visible: !backend.isMobile; text: qsTr("Open"); kind: "plain"
                            onClicked: backend.openDownloadFolder() }
                AppButton { visible: !backend.isMobile && page.s.download_dir !== ""; kind: "plain"; text: qsTr("Reset")
                            onClicked: backend.setDownloadDir("") }
            }
            SettingsItem {
                label: qsTr("Parallel downloads")
                icon: "layers"
                summary: String(page.s.max_parallel)
                hint: qsTr("How many links are downloaded at the same time.")
                Stepper {
                    value: page.s.max_parallel
                    from: 1
                    to: 4
                    onMoved: (v) => backend.setSetting("max_parallel", v)
                }
            }
            SettingsItem {
                visible: backend.mp3TagsAvailable
                label: qsTr("Ask whether to edit MP3 tags")
                icon: "tag"
                summary: page.s.ask_mp3_tags ? qsTr("Yes") : qsTr("No")
                hint: qsTr("After an MP3 download, a short question appears. The answer is No by default. The tags are filled in from the video description either way.")
                stacked: false
                AppSwitch { checked: page.s.ask_mp3_tags; onToggled: backend.setSetting("ask_mp3_tags", checked) }
            }
            SettingsItem {
                label: qsTr("Create HTML pages")
                icon: "code"
                summary: page.s.html_create === "both" ? qsTr("Server + file") : page.s.html_create === "file" ? qsTr("File") : qsTr("Server")
                hint: page.s.html_create === "both"
                    ? qsTr("Two linked pages next to the file: one with the online player (server) and a standalone one (file). Links use only the file name.")
                    : page.s.html_create === "server"
                    ? qsTr("One page with the online player; it plays when opened through Yeal's local server.")
                    : qsTr("One standalone page that works from disk without Yeal or a server.")
                stacked: Theme.compact
                Segmented {
                    current: page.s.html_create
                    options: [{ text: qsTr("Server"), value: "server" },
                              { text: qsTr("File"), value: "file" },
                              { text: qsTr("Both"), value: "both" }]
                    Layout.preferredWidth: 290
                    onActivated: (v) => backend.setSetting("html_create", v)
                }
            }
            SettingsItem {
                label: qsTr("Play only one media at a time")
                icon: "play"
                summary: page.s.single_playback ? qsTr("On") : qsTr("Off")
                hint: qsTr("In saved HTML pages the local player and the online player pause each other, so they never play together. Applies to pages created from now on.")
                stacked: false
                AppSwitch { checked: page.s.single_playback; onToggled: backend.setSetting("single_playback", checked) }
            }
            SettingsItem {
                label: qsTr("Open saved HTML pages")
                icon: "globe"
                summary: page.s.html_open_mode === "server" ? qsTr("Local server") : qsTr("Local file")
                hint: page.s.html_open_mode === "server"
                    ? qsTr("Local server (127.0.0.1): embedded YouTube players work while Yeal is running.")
                    : qsTr("Local file: works without Yeal or a server; YouTube opens on the original site.")
                stacked: Theme.compact
                Segmented {
                    current: page.s.html_open_mode
                    options: [{ text: qsTr("Local file"), value: "file" },
                              { text: qsTr("Local server"), value: "server" }]
                    Layout.preferredWidth: 290
                    onActivated: (v) => backend.setSetting("html_open_mode", v)
                }
            }
            SettingsItem {
                label: qsTr("Speed limit")
                icon: "gauge"
                summary: page.s.rate_limit_kbps > 0 ? qsTr("%1 KB/s").arg(page.s.rate_limit_kbps) : qsTr("Unlimited")
                hint: qsTr("In KB/s per download. 0 means unlimited.")
                AppField {
                    id: rateField
                    text: page.s.rate_limit_kbps
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 10000000 }
                    horizontalAlignment: TextInput.AlignRight
                    Layout.preferredWidth: 120
                    onEditingFinished: backend.setSetting("rate_limit_kbps", text === "" ? 0 : parseInt(text))
                    Accessible.name: qsTr("Speed limit in KB per second")
                }
            }
            SettingsItem {
                label: qsTr("Gentle mode")
                icon: "shield"
                summary: page.s.gentle_mode ? qsTr("On") : qsTr("Off")
                hint: qsTr("Recommended. Pauses between requests, waits longer after errors, pauses the queue when YouTube asks to slow down.")
                stacked: false
                AppSwitch { checked: page.s.gentle_mode; onToggled: backend.setSetting("gentle_mode", checked) }
            }
            SettingsItem {
                label: qsTr("Use browser login for downloads")
                icon: "lock"
                summary: page.s.cookies_browser === "" ? qsTr("Off") : page.s.cookies_browser.charAt(0).toUpperCase() + page.s.cookies_browser.slice(1)
                hint: qsTr("For protected videos: sign in to YouTube in Firefox, Edge or Chrome, select the same browser here, then close it before retrying. Google may refuse sign-in inside Yeal's embedded browser. Firefox works best: Chrome and Edge protect their cookies, so Yeal may not be able to read them (it then downloads without login).")
                stacked: false
                Segmented {
                    current: page.s.cookies_browser
                    options: [{ text: qsTr("Off"), value: "" }, { text: "Firefox", value: "firefox" },
                              { text: "Edge", value: "edge" }, { text: "Chrome", value: "chrome" }]
                    Layout.preferredWidth: 300
                    onActivated: (v) => backend.setCookiesBrowser(v)
                }
            }
            SettingsItem {
                label: qsTr("Proxy")
                icon: "network"
                summary: page.s.proxy !== "" ? page.s.proxy : qsTr("None")
                hint: proxyError.text !== "" ? proxyError.text : qsTr("Optional, e.g. socks5://127.0.0.1:9050")
                stacked: true
                AppField {
                    id: proxyField
                    text: page.s.proxy
                    placeholderText: qsTr("No proxy")
                    Layout.fillWidth: true
                    onEditingFinished: proxyError.text = backend.setProxy(text)
                    Accessible.name: qsTr("Proxy address")
                    Text { id: proxyError; visible: false }
                }
            }
        }

        SettingsGroup {
            title: qsTr("Streaming")
            icon: "cast"
            collapsible: true
            visible: backend.streamAvailable
            Layout.fillWidth: true
            footer: qsTr("Plays finished downloads on speakers and TVs in your Wi-Fi/LAN (UPnP/DLNA), e.g. KEF LS50 Wireless I and II. Yeal serves the file and the device fetches it. Windows may ask once to allow Yeal in the firewall: choose \"Private networks\".")
            SettingsItem {
                label: qsTr("Speaker / TV (box)")
                icon: "speaker"
                summary: page.s.stream_device && page.s.stream_device.name ? page.s.stream_device.name : qsTr("Not chosen")
                hint: backend.streamStatus !== "" ? backend.streamStatus
                    : qsTr("Search the network, then tap a device. It is used by the Stream button of every download.")
                stacked: true
                ColumnLayout {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    RowLayout {
                        spacing: Theme.s2
                        AppButton { text: backend.streamScanning ? qsTr("Searching…") : qsTr("Search network"); iconName: "wifi"
                                    enabled: !backend.streamScanning; onClicked: backend.scanStreamDevices() }
                        AppButton { visible: !!(page.s.stream_device && page.s.stream_device.id); text: qsTr("Forget"); kind: "plain"
                                    onClicked: backend.clearStreamDevice() }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.s2
                        Repeater {
                            model: backend.streamDevices
                            delegate: Chip {
                                required property var modelData
                                text: modelData.name + (modelData.online ? "" : qsTr(" (not seen)"))
                                checked: modelData.selected
                                onToggled: backend.selectStreamDevice(modelData.id)
                            }
                        }
                    }
                }
            }
            SettingsItem {
                label: qsTr("Add device by address")
                icon: "network"
                summary: page.s.stream_hosts.length > 0 ? qsTr("%1 saved").arg(page.s.stream_hosts.length) : qsTr("None")
                hint: streamHostError.text !== "" ? streamHostError.text
                    : qsTr("Use this when the search does not find your device: its IP address (see your router or the KEF app), a device name, or the full description URL.")
                stacked: true
                ColumnLayout {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    RowLayout {
                        spacing: Theme.s2
                        Layout.fillWidth: true
                        AppField {
                            id: streamHostField
                            placeholderText: qsTr("e.g. 192.168.1.50")
                            Layout.fillWidth: true
                            onAccepted: streamHostAdd.clicked()
                            Accessible.name: qsTr("Device address")
                        }
                        AppButton {
                            id: streamHostAdd
                            text: qsTr("Add")
                            onClicked: {
                                streamHostError.text = backend.addStreamHost(streamHostField.text)
                                if (streamHostError.text === "") streamHostField.text = ""
                            }
                        }
                    }
                    Flow {
                        Layout.fillWidth: true
                        spacing: Theme.s2
                        Repeater {
                            model: page.s.stream_hosts
                            delegate: AppButton {
                                required property var modelData
                                text: modelData
                                iconName: "x"
                                kind: "plain"
                                onClicked: backend.removeStreamHost(modelData)
                                Accessible.name: qsTr("Remove %1").arg(modelData)
                            }
                        }
                    }
                    Text { id: streamHostError; visible: false; text: "" }
                }
            }
            SettingsItem {
                label: qsTr("Start volume")
                icon: "gauge"
                summary: page.s.stream_volume >= 0 ? page.s.stream_volume + "%" : qsTr("Device volume")
                hint: qsTr("Volume (0-100) set on the speaker before a stream starts. Leave empty to keep the volume the device already has.")
                AppField {
                    text: page.s.stream_volume >= 0 ? String(page.s.stream_volume) : ""
                    placeholderText: qsTr("Keep")
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 100 }
                    horizontalAlignment: TextInput.AlignRight
                    Layout.preferredWidth: 120
                    onEditingFinished: backend.setSetting("stream_volume", text === "" ? -1 : parseInt(text))
                    Accessible.name: qsTr("Start volume in percent")
                }
            }
            SettingsItem {
                label: qsTr("Search time")
                icon: "clock"
                summary: qsTr("%1 s").arg(page.s.stream_scan_seconds)
                hint: qsTr("How long Yeal waits for devices to answer when it searches the network. Increase it if a device is found only sometimes.")
                Stepper {
                    value: page.s.stream_scan_seconds
                    from: 2
                    to: 15
                    suffix: qsTr(" s")
                    onMoved: (v) => backend.setSetting("stream_scan_seconds", v)
                }
            }
            SettingsItem {
                label: qsTr("Media server port")
                icon: "network"
                summary: page.s.stream_port > 0 ? String(page.s.stream_port) : qsTr("Automatic")
                hint: qsTr("Port that the speaker uses to fetch the file from this PC. 0 = automatic. If the Windows firewall blocks streaming, enter a fixed port (1024-65535) and allow it for private networks.")
                AppField {
                    text: String(page.s.stream_port)
                    inputMethodHints: Qt.ImhDigitsOnly
                    validator: IntValidator { bottom: 0; top: 65535 }
                    horizontalAlignment: TextInput.AlignRight
                    Layout.preferredWidth: 120
                    onEditingFinished: backend.setSetting("stream_port", text === "" ? 0 : parseInt(text))
                    Accessible.name: qsTr("Media server port")
                }
            }
        }

        SettingsGroup {
            title: qsTr("Download engine")
            icon: "cpu"
            collapsible: true
            Layout.fillWidth: true
            footer: qsTr("yt-dlp is checked for updates every few days. Updating keeps downloads working when sites change.")
            SettingsItem {
                label: qsTr("yt-dlp")
                icon: "download"
                summary: backend.ytdlpBusy ? qsTr("Updating…") : backend.ytdlpVersion
                hint: backend.ytdlpBusy ? qsTr("Updating…") : qsTr("Version %1").arg(backend.ytdlpVersion)
                AppButton { text: qsTr("Update now"); iconName: "retry"; enabled: !backend.ytdlpBusy
                            onClicked: backend.updateYtDlp() }
            }
            SettingsItem {
                label: qsTr("Update automatically")
                icon: "retry"
                summary: page.s.auto_update ? qsTr("On") : qsTr("Off")
                stacked: false
                AppSwitch { checked: page.s.auto_update; onToggled: backend.setSetting("auto_update", checked) }
            }
            SettingsItem {
                label: qsTr("ffmpeg")
                icon: "film"
                summary: backend.ffmpegAvailable ? qsTr("Ready") : qsTr("Missing")
                hint: backend.ffmpegAvailable
                    ? qsTr("Version %1\n%2").arg(backend.ffmpegVersion || qsTr("unknown")).arg(backend.ffmpegPath)
                    : qsTr("Not found – expected at %1").arg(backend.ffmpegDefaultPath)
                stacked: true
                Badge { text: backend.ffmpegAvailable ? qsTr("Ready") : qsTr("Missing")
                        kind: backend.ffmpegAvailable ? "success" : "warning" }
                AppButton { visible: !backend.isMobile; text: qsTr("Choose…"); iconName: "folder"
                            onClicked: ffmpegLoader.item.open() }
                AppButton { visible: !backend.isMobile; text: qsTr("Automatic"); kind: "plain"
                            onClicked: {
                                var err = backend.setHelperPath("ffmpeg", "")
                                page.toastRequest(err || qsTr("ffmpeg path detected again"))
                            } }
                AppButton { visible: !backend.isMobile; text: qsTr("Update…"); iconName: "open"; kind: "plain"
                            onClicked: backend.openLink("https://ffmpeg.org/download.html") }
            }
            SettingsItem {
                label: qsTr("Node.js JavaScript runtime")
                icon: "code"
                summary: backend.jsRuntimeAvailable ? qsTr("Ready") : qsTr("Missing")
                hint: backend.jsRuntimeAvailable
                    ? qsTr("Version %1\n%2").arg(backend.jsRuntimeVersion || qsTr("unknown")).arg(backend.jsRuntimePath)
                    : qsTr("Not found – expected at %1").arg(backend.jsRuntimeDefaultPath)
                stacked: true
                Badge { text: backend.jsRuntimeAvailable ? qsTr("Ready") : qsTr("Missing")
                        kind: backend.jsRuntimeAvailable ? "success" : "warning" }
                AppButton { visible: !backend.isMobile; text: qsTr("Choose…"); iconName: "folder"
                            onClicked: nodeLoader.item.open() }
                AppButton { visible: !backend.isMobile; text: qsTr("Automatic"); kind: "plain"
                            onClicked: {
                                var err = backend.setHelperPath("node", "")
                                page.toastRequest(err || qsTr("Node.js path detected again"))
                            } }
                AppButton { visible: !backend.isMobile; text: qsTr("Update…"); iconName: "open"; kind: "plain"
                            onClicked: backend.openLink("https://nodejs.org/en/download") }
            }
        }

        SettingsGroup {
            title: qsTr("Advanced")
            icon: "terminal"
            collapsible: true
            Layout.fillWidth: true
            footer: customError.text !== "" ? customError.text
                : qsTr("Extra yt-dlp options as a JSON object, applied to every download. Unsafe options are rejected.")
            SettingsItem {
                label: qsTr("Custom yt-dlp options")
                icon: "terminal"
                stacked: true
                ColumnLayout {
                    spacing: Theme.s2
                    Layout.fillWidth: true
                    ScrollView {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 110
                        TextArea {
                            id: customArea
                            text: page.s.custom_options
                            placeholderText: "{\"retries\": 5}"
                            font.family: "Consolas, Menlo, monospace"
                            font.pixelSize: Theme.footnote + 1
                            color: Theme.text
                            placeholderTextColor: Theme.textTertiary
                            wrapMode: TextArea.Wrap
                            padding: Theme.s3
                            background: Rectangle {
                                radius: Theme.radius
                                color: Theme.field
                                border.width: customArea.activeFocus ? 2 : 0
                                border.color: Theme.accent
                            }
                            Accessible.name: qsTr("Custom yt-dlp options (JSON)")
                        }
                    }
                    AppButton {
                        text: qsTr("Apply")
                        onClicked: {
                            customError.text = backend.setCustomOptions(customArea.text)
                            if (customError.text === "") page.toastRequest(qsTr("Options saved"))
                        }
                    }
                    Text { id: customError; visible: false; text: "" }
                }
            }
        }

        SettingsGroup {
            title: qsTr("Admin")
            icon: "lock"
            collapsible: true
            visible: backend.vaultAvailable
            Layout.fillWidth: true
            AdminPanel {}
        }

        SettingsGroup {
            title: qsTr("Tidal")
            icon: "music"
            collapsible: true
            visible: !backend.isMobile
            Layout.fillWidth: true
            SettingsItem {
                label: qsTr("Tidal subscription required")
                icon: "info"
                summary: qsTr("Only with a Tidal subscription")
                hint: backend.tidalNotice
                stacked: true
            }
            SettingsItem {
                label: qsTr("Tidal helper (tiddl)")
                icon: "code"
                summary: backend.tidalInstalled ? qsTr("Ready") : qsTr("Missing")
                hint: backend.tidalInstalled ? backend.tidalExe : backend.tidalInstallHint
                stacked: true
                Badge { text: backend.tidalInstalled ? qsTr("Ready") : qsTr("Missing")
                        kind: backend.tidalInstalled ? "success" : "warning" }
                AppButton { text: qsTr("Choose…"); iconName: "folder"; onClicked: tiddlLoader.item.open() }
                AppButton { text: qsTr("Automatic"); kind: "plain"
                            onClicked: page.toastRequest(backend.setTidalPath("") || qsTr("tiddl is detected again")) }
                AppButton { text: qsTr("Download…"); iconName: "open"; kind: "plain"
                            onClicked: backend.openLink("https://github.com/oskvr37/tiddl") }
            }
            SettingsItem {
                label: qsTr("Tidal account")
                icon: "lock"
                summary: backend.tidalLoggedIn ? qsTr("Signed in") : backend.tidalLoginRunning ? qsTr("Waiting for the browser…") : qsTr("Signed out")
                hint: qsTr("Each user signs in with their own Tidal account in the browser. Yeal never sees the password.")
                stacked: true
                Badge { text: backend.tidalLoggedIn ? qsTr("Signed in") : qsTr("Signed out")
                        kind: backend.tidalLoggedIn ? "success" : "neutral" }
                AppButton { visible: !backend.tidalLoggedIn && !backend.tidalLoginRunning; text: qsTr("Sign in…"); iconName: "lock"
                            enabled: backend.tidalInstalled
                            onClicked: { var err = backend.tidalLogin(); if (err) page.toastRequest(err) } }
                AppButton { visible: backend.tidalLoginRunning; text: qsTr("Cancel"); kind: "plain"
                            onClicked: backend.tidalCancelLogin() }
                AppButton { visible: backend.tidalLoggedIn; text: qsTr("Sign out"); kind: "plain"
                            onClicked: backend.tidalLogout() }
                AppButton { text: qsTr("Check"); kind: "plain"; onClicked: backend.tidalRefresh() }
            }
            SettingsItem {
                label: qsTr("Quality")
                icon: "music"
                summary: page.s.tidal_quality === "max" ? qsTr("Max (FLAC, up to 24-bit)") : page.s.tidal_quality === "high" ? qsTr("High (FLAC 16-bit)")
                         : page.s.tidal_quality === "normal" ? qsTr("Normal (AAC 320)") : qsTr("Low (AAC 96)")
                hint: qsTr("What your subscription offers is used; Max needs a plan with HiFi Plus / Max.")
                stacked: Theme.compact
                Segmented {
                    current: page.s.tidal_quality
                    options: [{ text: qsTr("Low"), value: "low" }, { text: qsTr("Normal"), value: "normal" },
                              { text: qsTr("High"), value: "high" }, { text: qsTr("Max"), value: "max" }]
                    Layout.fillWidth: Theme.compact
                    Layout.preferredWidth: 340
                    onActivated: (v) => backend.setSetting("tidal_quality", v)
                }
            }
            SettingsItem {
                label: qsTr("Parallel Tidal tracks")
                icon: "layers"
                summary: String(page.s.tidal_threads)
                hint: qsTr("Keep this low: many parallel requests can get a Tidal account blocked.")
                Stepper {
                    value: page.s.tidal_threads
                    from: 1
                    to: 4
                    onMoved: (v) => backend.setSetting("tidal_threads", v)
                }
            }
        }

        SettingsGroup {
            title: qsTr("Info")
            icon: "info"
            collapsible: true
            Layout.fillWidth: true
            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: Math.min(width, 420) * 2 / 3 + 2 * Theme.s4
                Image {
                    anchors.centerIn: parent
                    width: Math.min(parent.width - 2 * Theme.s4, 420)
                    height: width * 2 / 3
                    source: "assets/logo_card.png"
                    sourceSize.width: 960
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    Accessible.name: qsTr("Yeal logo")
                }
            }
            SettingsItem { label: qsTr("Yeal"); icon: "info"; summary: backend.appVersion }
            SettingsItem {
                label: qsTr("Tidal")
                icon: "music"
                visible: !backend.isMobile
                summary: qsTr("Only with a Tidal subscription")
                hint: backend.tidalNotice
                stacked: true
            }
            SettingsItem { label: qsTr("Platform"); icon: "window"; summary: backend.platformName }
            SettingsItem {
                id: historyRow
                property bool open: false
                label: qsTr("Version history")
                icon: "clock"
                hint: qsTr("Changes in this and previous Yeal versions")
                stacked: true
                ColumnLayout {
                    Layout.fillWidth: true
                    AppButton { text: historyRow.open ? qsTr("Hide") : qsTr("Show"); kind: "plain"
                                iconName: historyRow.open ? "chevronDown" : "chevronRight"
                                onClicked: historyRow.open = !historyRow.open }
                    ScrollView {
                        visible: historyRow.open
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300
                        TextArea {
                            text: backend.versionHistory
                            readOnly: true
                            selectByMouse: true
                            wrapMode: TextArea.Wrap
                            color: Theme.text
                            font.family: "Consolas, Menlo, monospace"
                            font.pixelSize: Theme.caption + 1
                            background: Rectangle { color: Theme.field; radius: Theme.radius }
                        }
                    }
                }
            }
            SettingsItem {
                id: licensesRow
                property bool open: false
                label: qsTr("Module licenses")
                icon: "doc"
                hint: qsTr("Versions and licenses of the included runtime modules")
                stacked: true
                ColumnLayout {
                    Layout.fillWidth: true
                    AppButton { text: licensesRow.open ? qsTr("Hide") : qsTr("Show"); kind: "plain"
                                iconName: licensesRow.open ? "chevronDown" : "chevronRight"
                                onClicked: licensesRow.open = !licensesRow.open }
                    Text {
                        visible: licensesRow.open
                        text: backend.thirdPartyLicenses
                        color: Theme.textSecondary
                        font.pixelSize: Theme.footnote
                        wrapMode: Text.Wrap
                        Layout.fillWidth: true
                        Layout.topMargin: Theme.s2
                    }
                }
            }
        }
        Item { Layout.preferredHeight: Theme.s2 }
    }
}
