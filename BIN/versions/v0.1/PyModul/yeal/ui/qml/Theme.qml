pragma Singleton
import QtQuick

// Semantic design tokens. Light/dark is switched by `dark`; everything else derives from it.
QtObject {
    id: t
    property bool dark: false
    property bool compact: false
    // Content area (window coordinates) that dialogs are confined to: the area right/left of the bar.
    property rect dialogArea: Qt.rect(0, 0, 0, 0)
    readonly property bool reducedMotion: false

    // surfaces
    readonly property color window: dark ? "#121214" : "#F5F5F7"
    readonly property color sidebar: dark ? "#18181A" : "#EDEDF0"
    readonly property color surface: dark ? "#1E1E21" : "#FFFFFF"
    readonly property color raised: dark ? "#2A2A2D" : "#FFFFFF"
    readonly property color field: dark ? "#2C2C30" : "#EBEBF0"
    readonly property color hover: dark ? "#14FFFFFF" : "#0D000000"
    readonly property color pressed: dark ? "#22FFFFFF" : "#19000000"
    readonly property color separator: dark ? "#38383C" : "#E5E5EA"
    readonly property color track: dark ? "#3A3A3E" : "#E1E1E6"

    // text
    readonly property color text: dark ? "#F5F5F7" : "#1D1D1F"
    readonly property color textSecondary: dark ? "#A1A1A6" : "#6E6E73"
    readonly property color textTertiary: dark ? "#6E6E73" : "#8E8E93"

    // accent and status
    readonly property color accent: dark ? "#2997FF" : "#0071E3"      // text/icons on surfaces
    readonly property color accentFill: dark ? "#0A74E6" : "#0071E3"  // button fills
    readonly property color textOnAccent: "#FFFFFF"
    readonly property color accentSoft: dark ? "#330A74E6" : "#1A0071E3"
    readonly property color danger: dark ? "#FF6961" : "#D70015"
    readonly property color dangerSoft: dark ? "#26FF6961" : "#1AD70015"
    readonly property color success: dark ? "#30D158" : "#248A3D"
    readonly property color successSoft: dark ? "#2630D158" : "#1A248A3D"
    readonly property color warning: dark ? "#FF9F0A" : "#B25000"
    readonly property color warningSoft: dark ? "#26FF9F0A" : "#1AB25000"
    readonly property color shadow: dark ? "#66000000" : "#1A000000"

    // type scale
    readonly property int caption: 12
    readonly property int footnote: 13
    readonly property int body: 15
    readonly property int headline: 17
    readonly property int title: 22
    readonly property int largeTitle: 28

    // spacing and shape
    readonly property int s1: 4
    readonly property int s2: 8
    readonly property int s3: 12
    readonly property int s4: 16
    readonly property int s5: 24
    readonly property int s6: 32
    readonly property int radius: 10
    readonly property int radiusCard: 14
    readonly property int control: 36        // standard control height
    readonly property int touch: compact ? 44 : 36
    readonly property int durFast: reducedMotion ? 0 : 120
    readonly property int dur: reducedMotion ? 0 : 200
}
