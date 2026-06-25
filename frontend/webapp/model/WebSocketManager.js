sap.ui.define([
    "sap/base/Log",
    "sap/m/MessageToast"
], function (Log, MessageToast) {
    "use strict";

    /**
     * WebSocket manager — handles connections to Django Channels
     * for real-time price ticks, analysis updates, pattern matches, and alerts.
     */
    var WebSocketManager = function (oComponent) {
        this._component = oComponent;
        this._sockets = {};
        this._reconnectTimers = {};
        this._reconnectAttempts = {};
        this._maxReconnectAttempts = 10;
        this._reconnectDelay = 3000;

        // Derive WebSocket URL from current page location (works in dev + production)
        var sProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
        this._baseUrl = sProtocol + "//" + window.location.host;

        // Connect to overview + alerts on startup
        this.connect("overview", this._baseUrl + "/ws/overview/");
        this.connect("alerts", this._baseUrl + "/ws/alerts/");
    };

    WebSocketManager.prototype.connect = function (sName, sUrl) {
        var that = this;

        if (this._sockets[sName] && this._sockets[sName].readyState === WebSocket.OPEN) {
            return;
        }

        // Check reconnect limit
        if ((this._reconnectAttempts[sName] || 0) >= this._maxReconnectAttempts) {
            Log.error("Max reconnect attempts reached for: " + sName);
            return;
        }

        try {
            var ws = new WebSocket(sUrl);

            ws.onopen = function () {
                Log.info("WebSocket connected: " + sName);
                that._reconnectAttempts[sName] = 0;
                that._component.getModel().setProperty("/wsConnected", true);
                if (that._reconnectTimers[sName]) {
                    clearTimeout(that._reconnectTimers[sName]);
                    delete that._reconnectTimers[sName];
                }
            };

            ws.onmessage = function (event) {
                try {
                    var data = JSON.parse(event.data);
                    that._handleMessage(sName, data);
                } catch (e) {
                    Log.error("WebSocket parse error: " + e.message);
                }
            };

            ws.onclose = function () {
                Log.warning("WebSocket closed: " + sName);
                delete that._sockets[sName];

                // Update connection status — false only when no sockets remain open
                var bAnyOpen = Object.keys(that._sockets).some(function (key) {
                    return that._sockets[key] && that._sockets[key].readyState === WebSocket.OPEN;
                });
                if (!bAnyOpen) {
                    that._component.getModel().setProperty("/wsConnected", false);
                }

                // Don't reconnect if explicitly disconnected
                if (that._explicitDisconnect && that._explicitDisconnect[sName]) {
                    delete that._explicitDisconnect[sName];
                    return;
                }

                // Auto-reconnect with limit
                that._reconnectAttempts[sName] = (that._reconnectAttempts[sName] || 0) + 1;
                that._reconnectTimers[sName] = setTimeout(function () {
                    Log.info("Reconnecting WebSocket: " + sName + " (attempt " + that._reconnectAttempts[sName] + ")");
                    that.connect(sName, sUrl);
                }, that._reconnectDelay);
            };

            ws.onerror = function () {
                Log.error("WebSocket error: " + sName);
            };

            this._sockets[sName] = ws;
        } catch (e) {
            Log.error("WebSocket connection failed: " + e.message);
        }
    };

    WebSocketManager.prototype.connectPair = function (sPair) {
        var sName = "pair_" + sPair.toLowerCase();
        var sUrl = this._baseUrl + "/ws/pair/" + sPair + "/";
        this._reconnectAttempts[sName] = 0; // Reset on explicit connect
        this.connect(sName, sUrl);
    };

    WebSocketManager.prototype.disconnectPair = function (sPair) {
        var sName = "pair_" + sPair.toLowerCase();
        if (!this._explicitDisconnect) {
            this._explicitDisconnect = {};
        }
        this._explicitDisconnect[sName] = true;
        if (this._sockets[sName]) {
            this._sockets[sName].close();
            delete this._sockets[sName];
        }
        if (this._reconnectTimers[sName]) {
            clearTimeout(this._reconnectTimers[sName]);
            delete this._reconnectTimers[sName];
        }
    };

    WebSocketManager.prototype._handleMessage = function (sSource, data) {
        var oComponent = this._component;
        var oMarketModel = oComponent.getModel("market");
        var oAnalysisModel = oComponent.getModel("analysis");
        var oAppModel = oComponent.getModel();

        if (data.type === "tick") {
            // Single pair tick update
            var sTicks = "/ticks/" + data.symbol;
            oMarketModel.setProperty(sTicks, data);

            // Update app model if this is the selected pair
            if (data.symbol === oAppModel.getProperty("/selectedPair")) {
                oAppModel.setProperty("/currentPrice", data.bid);
                oAppModel.setProperty("/spread", data.spread);
            }

        } else if (data.type === "ticks") {
            // All pairs ticks update
            oMarketModel.setProperty("/ticks", data.data);

        } else if (data.type === "analysis") {
            // Full analysis update for a pair
            if (data.pair === oAppModel.getProperty("/selectedPair")) {
                oAnalysisModel.setProperty("/timeframes", data.timeframes || {});
                oAnalysisModel.setProperty("/structure", data.structure || {});
                oAnalysisModel.setProperty("/liquidity", data.liquidity || {});
                oAnalysisModel.setProperty("/session", data.session || {});
                oAnalysisModel.setProperty("/sr_zones", data.sr_zones || []);
                oAnalysisModel.setProperty("/key_levels", data.key_levels || {});

                // Trade score
                if (data.trade_score !== undefined) {
                    oAnalysisModel.setProperty("/tradeScore", data.trade_score);
                    oAnalysisModel.setProperty("/scoreBreakdown", data.score_breakdown || {});
                }

                // Extract main trend from H1
                var oH1 = data.timeframes ? data.timeframes["H1"] : null;
                if (oH1) {
                    oAnalysisModel.setProperty("/trendScore", oH1.trend_score);
                    oAnalysisModel.setProperty("/trendDirection", oH1.trend_direction);
                }
            }

        } else if (data.type === "pattern_match") {
            // Live pattern overlay data
            if (data.pair === oAppModel.getProperty("/selectedPair")) {
                oAppModel.setProperty("/patternMatches", data.matches || []);
            }

        } else if (data.alert_type) {
            // Alert notification
            this._showAlert(data);
        }
    };

    WebSocketManager.prototype._showAlert = function (data) {
        MessageToast.show(
            data.message || "Alert: " + data.alert_type,
            { duration: 5000 }
        );

        // Browser notification
        if ("Notification" in window && Notification.permission === "granted") {
            try {
                new Notification("Forex Alert", {
                    body: data.message || data.alert_type
                });
            } catch (e) {
                // Notification API not available
            }
        }
    };

    WebSocketManager.prototype.destroy = function () {
        var that = this;

        Object.keys(this._sockets).forEach(function (key) {
            if (that._sockets[key]) {
                that._sockets[key].close();
            }
        });
        this._sockets = {};

        Object.keys(this._reconnectTimers).forEach(function (key) {
            clearTimeout(that._reconnectTimers[key]);
        });
        this._reconnectTimers = {};
    };

    return WebSocketManager;
});
