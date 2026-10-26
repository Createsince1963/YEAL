import QtQuick

// One data request of the TIDAL DIY view: route + arg -> data (via tidal.load / tidal.pageLoaded).
// Answers of older requests are ignored, so switching pages quickly never shows stale data.
QtObject {
    id: req
    property string route
    property string arg: ""
    property bool auto: true             // load as soon as route/arg are set
    property var data: null
    property bool loading: false
    property string error: ""
    property string _id: ""
    signal loaded()

    function reload() {
        if (route === "") return
        error = ""
        loading = true
        _id = tidal.load(route, arg)
    }
    onRouteChanged: if (auto) Qt.callLater(reload)
    onArgChanged: if (auto) Qt.callLater(reload)
    Component.onCompleted: if (auto && route !== "") Qt.callLater(reload)

    property Connections _c: Connections {
        target: tidal
        function onPageLoaded(rid, route, data) {
            if (rid !== req._id) return
            req.data = data
            req.loading = false
            req.loaded()
        }
        function onPageFailed(rid, route, message) {
            if (rid !== req._id) return
            req.error = message
            req.loading = false
        }
    }
}
