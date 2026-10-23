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

    ColumnLayout {
        id: column
        x: Theme.compact ? Theme.s4 : Theme.s6
        y: Theme.compact ? Theme.s4 : Theme.s5
        width: Math.min(720, page.width - 2 * (Theme.compact ? Theme.s4 : Theme.s6))
        spacing: Theme.s5

        Text {
            text: qsTr("Settings")
            font.pixelSize: Theme.compact ? Theme.title : Theme.largeTitle
            font.weight: Font.DemiBold
            color: Theme.text
            Accessible.role: Accessible.Heading
        }

        SettingsGroup {
            title: qsTr("Browser")
            visible: backend.browserAvailable
            Layout.fillWidth: true
            SettingsRow {
                label: qsTr("YouTube browser on the Downloads page")
                hint: qsTr("Uses the Microsoft Edge WebView2 of Windows. Opening a video fills the link field.")
                stacked: false
                AppSwitch { checked: page.s.show_browser; onToggled: backend.setSetting("show_browser", checked) }
            }
            SettingsRow {
                label: qsTr("Block ads and trackers in the browser (experimental)")
                hint: qsTr("Refuses known ad and tracker domains (own list: blocklist.txt in the Yeal data folder, hosts format). Video ads from YouTube itself are skipped by a script. Off by default. If YouTube misbehaves, leave it off. Takes effect after a restart.")
                stacked: false
                AppSwitch { checked: page.s.adblock_experimental; onToggled: backend.setSetting("adblock_experimental", checked) }
            }
        }

        SettingsGroup {
            title: qsTr("Appearance")
            Layout.fillWidth: true
            SettingsRow {
                label: qsTr("Theme")
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
            Layout.fillWidth: true
            SettingsRow {
                label: qsTr("Save to")
                hint: page.s.download_dir
                stacked: Theme.compact
                AppButton { visible: !backend.isMobile; text: qsTr("Choose…"); iconName: "folder"
                            onClicked: folderLoader.item.open() }
                AppButton { visible: !backend.isMobile; text: qsTr("Open"); kind: "plain"
                            onClicked: backend.openDownloadFolder() }
                AppButton { visible: !backend.isMobile && page.s.download_dir !== ""; kind: "plain"; text: qsTr("Reset")
                            onClicked: backend.setDownloadDir("") }
            }
            SettingsRow {
                label: qsTr("Parallel downloads")
                hint: qsTr("How many links are downloaded at the same time.")
                Stepper {
                    value: page.s.max_parallel
                    from: 1
                    to: 4
                    onMoved: (v) => backend.setSetting("max_parallel", v)
                }
            }
            SettingsRow {
                visible: backend.mp3TagsAvailable
                label: qsTr("Ask whether to edit MP3 tags")
                hint: qsTr("After an MP3 download, a short question appears. The answer is No by default. The tags are filled in from the video description either way.")
                stacked: false
                AppSwitch { checked: page.s.ask_mp3_tags; onToggled: backend.setSetting("ask_mp3_tags", checked) }
            }
            SettingsRow {
                label: qsTr("Speed limit")
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
            SettingsRow {
                label: qsTr("Gentle mode")
                hint: qsTr("Recommended. Pauses between requests, waits longer after errors, pauses the queue when YouTube asks to slow down.")
                stacked: false
                AppSwitch { checked: page.s.gentle_mode; onToggled: backend.setSetting("gentle_mode", checked) }
            }
            SettingsRow {
                label: qsTr("Use browser login for downloads")
                hint: qsTr("Optional: age-restricted, members-only or Premium videos. Reads the cookies of an installed browser (Firefox works best). Off by default.")
                stacked: false
                Segmented {
                    current: page.s.cookies_browser
                    options: [{ text: qsTr("Off"), value: "" }, { text: "Firefox", value: "firefox" },
                              { text: "Edge", value: "edge" }, { text: "Chrome", value: "chrome" }]
                    Layout.preferredWidth: 300
                    onActivated: (v) => backend.setCookiesBrowser(v)
                }
            }
            SettingsRow {
                label: qsTr("Proxy")
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
            title: qsTr("Download engine")
            Layout.fillWidth: true
            footer: qsTr("yt-dlp is checked for updates every few days. Updating keeps downloads working when sites change.")
            SettingsRow {
                label: qsTr("yt-dlp")
                hint: backend.ytdlpBusy ? qsTr("Updating…") : qsTr("Version %1").arg(backend.ytdlpVersion)
                AppButton { text: qsTr("Update now"); iconName: "retry"; enabled: !backend.ytdlpBusy
                            onClicked: backend.updateYtDlp() }
            }
            SettingsRow {
                label: qsTr("Update automatically")
                stacked: false
                AppSwitch { checked: page.s.auto_update; onToggled: backend.setSetting("auto_update", checked) }
            }
            SettingsRow {
                label: qsTr("ffmpeg")
                hint: backend.ffmpegAvailable ? qsTr("Merging and conversion available")
                                              : qsTr("Not found – only single-file formats can be downloaded")
                Badge { text: backend.ffmpegAvailable ? qsTr("Ready") : qsTr("Missing")
                        kind: backend.ffmpegAvailable ? "success" : "warning" }
            }
            SettingsRow {
                label: qsTr("JavaScript runtime")
                hint: backend.jsRuntimeAvailable ? qsTr("Needed for YouTube – available")
                                                 : qsTr("Node.js or Deno is required for YouTube")
                Badge { text: backend.jsRuntimeAvailable ? qsTr("Ready") : qsTr("Missing")
                        kind: backend.jsRuntimeAvailable ? "success" : "warning" }
            }
        }

        SettingsGroup {
            title: qsTr("Advanced")
            Layout.fillWidth: true
            footer: customError.text !== "" ? customError.text
                : qsTr("Extra yt-dlp options as a JSON object, applied to every download. Unsafe options are rejected.")
            SettingsRow {
                label: qsTr("Custom yt-dlp options")
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
            visible: backend.vaultAvailable
            Layout.fillWidth: true
            AdminPanel {}
        }

        SettingsGroup {
            title: qsTr("About")
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
            SettingsRow { label: qsTr("Yeal"); Text { text: backend.appVersion; color: Theme.textSecondary; font.pixelSize: Theme.body } }
            SettingsRow { label: qsTr("Platform"); Text { text: backend.platformName; color: Theme.textSecondary; font.pixelSize: Theme.body } }
        }
        Item { Layout.preferredHeight: Theme.s2 }
    }
}
