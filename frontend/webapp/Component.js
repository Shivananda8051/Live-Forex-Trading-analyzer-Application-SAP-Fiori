sap.ui.define([
    "sap/ui/core/UIComponent",
    "sap/ui/model/json/JSONModel",
    "forex/platform/model/WebSocketManager"
], function (UIComponent, JSONModel, WebSocketManager) {
    "use strict";

    return UIComponent.extend("forex.platform.Component", {

        metadata: {
            manifest: "json"
        },

        init: function () {
            UIComponent.prototype.init.apply(this, arguments);

            // Global app model (connection status, selected pair, etc.)
            var oAppModel = new JSONModel({
                selectedPair: "EURUSD",
                mt5Connected: false,
                wsConnected: false,
                currentPrice: 0,
                spread: 0,
                activeSession: ""
            });
            this.setModel(oAppModel);

            // Market data model (ticks for all pairs)
            var oMarketModel = new JSONModel({
                pairs: [],
                ticks: {}
            });
            this.setModel(oMarketModel, "market");

            // Analysis model (indicators, structure, liquidity per pair)
            var oAnalysisModel = new JSONModel({
                timeframes: {},
                structure: {},
                liquidity: {},
                session: {},
                tradeScore: 0,
                trendScore: 0,
                trendDirection: "neutral"
            });
            this.setModel(oAnalysisModel, "analysis");

            // Journal model
            var oJournalModel = new JSONModel({
                trades: [],
                analytics: {}
            });
            this.setModel(oJournalModel, "journal");

            // Initialize WebSocket manager
            this._wsManager = new WebSocketManager(this);

            // Initialize router
            this.getRouter().initialize();

            // Load initial data
            this._loadInitialData();
        },

        _loadInitialData: function () {
            var that = this;

            // Fetch session info
            jQuery.ajax({
                url: "/api/market/session/",
                method: "GET",
                timeout: 8000,
                success: function (data) {
                    that.getModel("analysis").setProperty("/session", data);
                    that.getModel().setProperty("/activeSession",
                        data.active_sessions ? data.active_sessions.join(" + ") : "Closed"
                    );
                },
                error: function () {
                    that.getModel().setProperty("/activeSession", "Offline");
                }
            });

            // Fetch latest ticks
            jQuery.ajax({
                url: "/api/market/ticks/",
                method: "GET",
                timeout: 8000,
                success: function (data) {
                    that.getModel("market").setProperty("/ticks", data);
                },
                error: function () {
                    // Backend not yet available — WebSocket will deliver ticks when ready
                }
            });
        },

        getWebSocketManager: function () {
            return this._wsManager;
        },

        destroy: function () {
            if (this._wsManager) {
                this._wsManager.destroy();
            }
            UIComponent.prototype.destroy.apply(this, arguments);
        }
    });
});
