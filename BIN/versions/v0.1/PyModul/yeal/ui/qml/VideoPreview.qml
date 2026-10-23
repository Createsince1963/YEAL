import QtQuick
import QtMultimedia

// Preview player: shows the frame at the selected time; can play the selected range.
Item {
    id: root
    property url source
    property real startSec: 0
    property real endSec: 0
    readonly property bool playing: player.playbackState === MediaPlayer.PlayingState
    property bool ready: false
    function seek(sec) {
        player.position = Math.round(sec * 1000)
        if (player.playbackState === MediaPlayer.StoppedState) player.pause()
    }
    function toggle() {
        if (playing) { player.pause(); return }
        player.position = Math.round(startSec * 1000)
        player.play()
    }

    MediaPlayer {
        id: player
        source: root.source
        videoOutput: out
        audioOutput: AudioOutput { volume: 0.6 }
        onMediaStatusChanged: if (mediaStatus === MediaPlayer.LoadedMedia && !root.ready) {
            root.ready = true
            root.seek(root.startSec)
        }
        onPositionChanged: if (playing && root.endSec > 0 && position >= root.endSec * 1000) player.pause()
    }
    Rectangle { anchors.fill: parent; color: "#000000"; radius: 8 }
    VideoOutput { id: out; anchors.fill: parent; fillMode: VideoOutput.PreserveAspectFit }
}
