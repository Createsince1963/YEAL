import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Primary button that doubles as a progress bar: while `progress` >= 0 a pill fills from the
// left. `progress` < 0 shows the normal button.
Button {
    id: control
    property string iconName: ""
    property real progress: -1
    readonly property bool showing: progress >= 0

    implicitHeight: Theme.touch
    implicitWidth: Math.max(150, row.implicitWidth + 2 * Theme.s5)
    hoverEnabled: true
    focusPolicy: Qt.StrongFocus
    font.pixelSize: Theme.body
    font.weight: Font.Medium

    background: Rectangle {
        radius: Theme.radius
        color: control.showing ? (Theme.dark ? "#123A66" : "#2E5F9E")
             : !control.enabled ? Theme.track
             : control.down ? Qt.darker(Theme.accentFill, 1.15)
             : control.hovered ? Qt.lighter(Theme.accentFill, 1.08) : Theme.accentFill
        border.width: control.visualFocus ? 2 : 0
        border.color: Theme.accent
        Behavior on color { ColorAnimation { duration: Theme.durFast } }

        Rectangle {
            visible: control.showing
            height: parent.height
            width: Math.max(parent.radius * 2, parent.width * Math.min(1, control.progress))
            radius: parent.radius
            color: Theme.accentFill
            Behavior on width { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }
        }
    }
    contentItem: RowLayout {
        id: row
        spacing: Theme.s2
        Item { Layout.fillWidth: true }
        Icon {
            visible: control.iconName !== ""
            name: control.iconName
            size: 18
            color: control.showing || control.enabled ? Theme.textOnAccent : Theme.textTertiary
        }
        Text {
            text: control.text
            font: control.font
            color: control.showing || control.enabled ? Theme.textOnAccent : Theme.textTertiary
            elide: Text.ElideRight
        }
        Item { Layout.fillWidth: true }
    }
    Accessible.role: showing ? Accessible.ProgressBar : Accessible.Button
    Accessible.name: text
}
