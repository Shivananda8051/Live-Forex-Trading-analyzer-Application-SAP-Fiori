sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "forex/platform/model/formatter"
], function (Controller, formatter) {
    "use strict";

    return Controller.extend("forex.platform.controller.Dashboard", {

        formatter: formatter,

        onInit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            oRouter.getRoute("dashboard").attachPatternMatched(this._onRouteMatched, this);

            // Clean up timer when navigating away from dashboard
            this.getOwnerComponent().getRouter().attachRouteMatched(this._onAnyRouteMatched, this);
        },

        _onRouteMatched: function () {
            this._active = true;
            this._loadAnalysis();
            this._loadNews();

            // Refresh data every 5 seconds for near-zero lag
            if (this._refreshTimer) {
                clearInterval(this._refreshTimer);
            }
            this._refreshTimer = setInterval(this._loadAnalysis.bind(this), 5000);
        },

        _onAnyRouteMatched: function (oEvent) {
            // Stop polling when navigating away from dashboard
            if (oEvent.getParameter("name") !== "dashboard" && this._active) {
                this._active = false;
                if (this._refreshTimer) {
                    clearInterval(this._refreshTimer);
                    this._refreshTimer = null;
                }
            }
        },

        _loadAnalysis: function () {
            var that = this;
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");

            jQuery.ajax({
                url: "/api/market/analysis/?pair=" + sPair,
                method: "GET",
                success: function (data) {
                    var oModel = that.getOwnerComponent().getModel("analysis");
                    oModel.setProperty("/timeframes", data.timeframes || {});
                    oModel.setProperty("/structure", data.structure || {});
                    oModel.setProperty("/liquidity", data.liquidity || {});

                    // Trade score from backend
                    if (data.trade_score !== undefined) {
                        oModel.setProperty("/tradeScore", data.trade_score);
                    }

                    // Key S/R levels
                    if (data.key_levels) {
                        oModel.setProperty("/key_levels", data.key_levels);
                    }

                    // Build scanner rows from timeframes
                    var aRows = [];
                    var oTF = data.timeframes || {};
                    ["M5", "M15", "H1", "H4", "D1"].forEach(function (tf) {
                        if (oTF[tf]) {
                            var row = Object.assign({}, oTF[tf]);
                            row.timeframe = tf;
                            if (row.ema_20 != null) row.ema_20 = parseFloat(row.ema_20).toFixed(5);
                            if (row.ema_50 != null) row.ema_50 = parseFloat(row.ema_50).toFixed(5);
                            if (row.ema_200 != null) row.ema_200 = parseFloat(row.ema_200).toFixed(5);
                            if (row.rsi != null) row.rsi = parseFloat(row.rsi).toFixed(1);
                            if (row.adx != null) row.adx = parseFloat(row.adx).toFixed(1);
                            aRows.push(row);
                        }
                    });
                    oModel.setProperty("/scannerRows", aRows);

                    // Set main trend from H1
                    if (oTF["H1"]) {
                        oModel.setProperty("/trendScore", oTF["H1"].trend_score);
                        oModel.setProperty("/trendDirection", oTF["H1"].trend_direction);
                    }
                },
                error: function () {
                    // Analysis not ready yet — Celery hasn't run or Redis empty
                }
            });
        },

        _loadNews: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/market/news/",
                method: "GET",
                success: function (data) {
                    that.getOwnerComponent().getModel().setProperty("/newsEvents", data || []);
                },
                error: function () {
                    that.getOwnerComponent().getModel().setProperty("/newsEvents", []);
                }
            });
        },

        onPairSelect: function (oEvent) {
            var oSource = oEvent.getSource();
            var sPair = oSource.data("pair");
            if (!sPair) return;

            var oAppModel = this.getOwnerComponent().getModel();
            var sOldPair = oAppModel.getProperty("/selectedPair");

            // Disconnect old pair's WebSocket
            var wsManager = this.getOwnerComponent().getWebSocketManager();
            if (sOldPair && sOldPair !== sPair) {
                wsManager.disconnectPair(sOldPair);
            }

            // Set new pair and connect
            oAppModel.setProperty("/selectedPair", sPair);
            wsManager.connectPair(sPair);

            // Reload analysis for new pair
            this._loadAnalysis();
        },

        onOpenChart: function () {
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");
            this.getOwnerComponent().getRouter().navTo("chart", { pair: sPair });
        },

        onExit: function () {
            if (this._refreshTimer) {
                clearInterval(this._refreshTimer);
                this._refreshTimer = null;
            }
        }
    });
});
