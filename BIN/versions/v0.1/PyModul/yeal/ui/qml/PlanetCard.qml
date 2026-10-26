import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

// The card that unfolds when a planet is opened (library, queue, played songs, settings, speaker). It fades and grows
// in, and folds away again with the X or by pressing the planet once more. The content is declared as children.
Rectangle {
    id: card
    property string title
    property bool open: false
    property color tint: Theme.accent
    property bool editable: false                      // the card has an edit mode: a pencil button zooms it
    property bool zoomed: false                        // edit mode: the card is large; "Done" brings it back to its normal size
    default property alias content: body.data
    signal closed()
    signal zoomRequested(bool on)

    radius: 22
    color: Qt.alpha(Theme.surface, 0.97)
    border.width: 1
    border.color: Qt.alpha(card.tint, 0.55)
    opacity: open ? 1 : 0
    scale: open ? 1 : 0.94
    visible: opacity > 0.01
    clip: true
    Behavior on opacity { NumberAnimation { duration: Theme.dur } }
    Behavior on scale { NumberAnimation { duration: Theme.dur; easing.type: Easing.OutCubic } }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.s3
        spacing: Theme.s2
        RowLayout {
            Layout.fillWidth: true
            Text { text: card.title; color: card.tint; font.pixelSize: Theme.footnote; font.weight: Font.Bold
                   font.letterSpacing: 1; Layout.fillWidth: true; elide: Text.ElideRight }
            AppButton {
                visible: card.editable && card.zoomed
                text: qsTr("Done"); kind: "primary"; iconName: "check"
                onClicked: card.zoomRequested(false)
            }
            IconButton {
                visible: card.editable && !card.zoomed
                implicitWidth: 26; implicitHeight: 26; iconName: "pencil"; tip: qsTr("Edit (the card grows)")
                onClicked: card.zoomRequested(true)
            }
            IconButton { implicitWidth: 26; implicitHeight: 26; iconName: "x"; tip: qsTr("Fold away"); onClicked: card.closed() }
        }
        Item { id: body; Layout.fillWidth: true; Layout.fillHeight: true }
    }
}
