import QtQuick

// Small status pill. kind: "neutral" | "accent" | "success" | "warning" | "danger"
Rectangle {
    id: root
    property string text
    property string kind: "neutral"
    readonly property color fg: kind === "accent" ? Theme.accent : kind === "success" ? Theme.success
        : kind === "warning" ? Theme.warning : kind === "danger" ? Theme.danger : Theme.textSecondary
    implicitWidth: label.implicitWidth + 16
    implicitHeight: 22
    radius: 11
    color: kind === "accent" ? Theme.accentSoft : kind === "success" ? Theme.successSoft
        : kind === "warning" ? Theme.warningSoft : kind === "danger" ? Theme.dangerSoft : Theme.field
    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        font.pixelSize: Theme.caption
        font.weight: Font.Medium
        color: root.fg
    }
    Accessible.role: Accessible.StaticText
    Accessible.name: text
}
