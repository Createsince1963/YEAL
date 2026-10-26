import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// Logo button that switches the right-hand player. A logo image (assets/<logo>) is shown when the file
// exists; otherwise an icon + the service name, so the button is never empty.
Rectangle {
    id: root
    property string logo: ""            // file name inside assets/, e.g. "logo_youtube.png"
    property string logoLight: ""       // the same for the light theme (e.g. a dark TIDAL mark); empty = the same file
    property string iconName
    property string text
    property string tip: ""             // tooltip (full name when the label is shortened)
    property bool selected: false
    signal clicked()

    implicitHeight: 40
    radius: Theme.radius
    color: selected ? Theme.accentSoft : mouse.hovered ? Theme.hover : "transparent"
    border.width: activeFocus ? 2 : (selected ? 1 : 0)
    border.color: activeFocus ? Theme.accent : Theme.separator
    activeFocusOnTab: true
    Keys.onReturnPressed: root.clicked()
    Keys.onSpacePressed: root.clicked()
    Accessible.role: Accessible.Button
    Accessible.name: text
    Accessible.checked: selected

    Image {
        id: img
        anchors.centerIn: parent
        source: root.logo !== "" ? "assets/" + (!Theme.dark && root.logoLight !== "" ? root.logoLight : root.logo) : ""
        sourceSize.height: 96
        fillMode: Image.PreserveAspectFit
        height: root.height - 2 * Theme.s2 + 2
        width: Math.min(implicitWidth * height / Math.max(1, implicitHeight), root.width - 2 * Theme.s3)
        smooth: true
        opacity: root.selected || mouse.hovered ? 1 : 0.7
        visible: status === Image.Ready
    }
    RowLayout {
        anchors.centerIn: parent
        width: Math.min(implicitWidth, root.width - 2 * Theme.s2)
        visible: img.status !== Image.Ready
        spacing: Theme.s2
        Icon { name: root.iconName; size: 20; color: root.selected ? Theme.accent : Theme.textSecondary }
        Text {
            text: root.text
            font.pixelSize: Theme.body
            font.weight: root.selected ? Font.Medium : Font.Normal
            color: root.selected ? Theme.accent : Theme.text
            elide: Text.ElideRight
            Layout.fillWidth: true
        }
    }
    HoverHandler { id: mouse }
    ToolTip.visible: tip !== "" && mouse.hovered && !Theme.compact
    ToolTip.delay: 600
    ToolTip.text: tip
    TapHandler { onTapped: root.clicked() }
}
