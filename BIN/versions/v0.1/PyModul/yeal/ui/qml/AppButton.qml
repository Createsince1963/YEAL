import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Button {
    id: control
    // "primary" | "secondary" | "plain" | "danger"
    property string kind: "secondary"
    property string iconName: ""

    implicitHeight: Theme.touch
    implicitWidth: Math.max(implicitHeight, row.implicitWidth + 2 * Theme.s4)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.pixelSize: Theme.body
    font.weight: Font.Medium

    readonly property color fg: !enabled ? Theme.textTertiary
        : kind === "primary" ? Theme.textOnAccent
        : kind === "danger" ? Theme.danger : kind === "plain" ? Theme.accent : Theme.text

    background: Rectangle {
        radius: Theme.radius
        color: {
            if (control.kind === "primary")
                return !control.enabled ? Theme.track
                    : control.down ? Qt.darker(Theme.accentFill, 1.15)
                    : control.hovered ? Qt.lighter(Theme.accentFill, 1.08) : Theme.accentFill
            if (control.kind === "plain")
                return control.down ? Theme.pressed : control.hovered ? Theme.hover : "transparent"
            return control.down ? Theme.pressed : control.hovered ? Qt.tint(Theme.field, Theme.hover) : Theme.field
        }
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: Theme.durFast } }
    }
    contentItem: RowLayout {
        id: row
        spacing: Theme.s2
        Icon {
            visible: control.iconName !== ""
            name: control.iconName
            color: control.fg
            size: 18
            Layout.alignment: Qt.AlignVCenter
        }
        Text {
            visible: control.text !== ""
            text: control.text
            font: control.font
            color: control.fg
            elide: Text.ElideRight
            Layout.alignment: Qt.AlignVCenter
        }
    }
    Accessible.role: Accessible.Button
    Accessible.name: text
}
