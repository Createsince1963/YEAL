pragma Singleton
import QtQuick

// 24x24 stroke icons (SVG path data).
QtObject {
    readonly property var d: ({
        "download": "M12 4v11 M7 11l5 5 5-5 M5 20h14",
        "plus": "M12 5v14 M5 12h14",
        "x": "M6 6l12 12 M18 6L6 18",
        "retry": "M20 12a8 8 0 1 1-2.6-5.9 M20 4v4.5h-4.5",
        "folder": "M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z",
        "sliders": "M4 7h9 M17 7h3 M4 17h3 M11 17h9 M15 4v6 M7 14v6",
        "stack": "M12 3l9 5-9 5-9-5z M3 12.5l9 5 9-5 M3 16.5l9 5 9-5",
        "trash": "M4 7h16 M9 7V4h6v3 M6 7l1 13h10l1-13",
        "copy": "M9 9h11v11H9z M5 15V4h11",
        "link": "M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1 M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1",
        "check": "M5 12.5l4.5 4.5L19 7",
        "chevronRight": "M9 5l7 7-7 7",
        "chevronDown": "M5 9l7 7 7-7",
        "open": "M14 4h6v6 M20 4l-9 9 M18 14v5H5V6h5",
        "clipboard": "M9 4h6v3H9z M7 5.5H5v15h14v-15h-2",
        "alert": "M12 9v4.5 M12 17v.01 M12 3.5l9.5 17h-19z",
        "search": "M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14z M16 16l4.5 4.5",
        "film": "M4 5h16v14H4z M8 5v14 M16 5v14 M4 12h16",
        "music": "M9 18V5l11-2v13 M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0z M20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z",
        "clock": "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z M12 7v5l3 2",
        "pencil": "M4 20l1-4L16 5l3 3L8 19z",
        "more": "M5 12v.01 M12 12v.01 M19 12v.01",
        "grid": "M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z",
        "play": "M7 4.5v15l12-7.5z",
        "pause": "M8 5v14 M16 5v14",
        "sparkle": "M12 3l2 6 6 2-6 2-2 6-2-6-6-2 6-2z"
    })
}
