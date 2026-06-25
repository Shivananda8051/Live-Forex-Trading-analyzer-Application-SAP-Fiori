sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/MessageToast",
    "sap/m/Text",
    "sap/m/ObjectStatus"
], function (Controller, MessageToast, Text, ObjectStatus) {
    "use strict";

    return Controller.extend("forex.platform.controller.Settings", {

        onInit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            oRouter.getRoute("settings").attachPatternMatched(this._onRouteMatched, this);
        },

        _onRouteMatched: function () {
            this._loadSettings();
            this._loadMT5Status();
        },

        _loadSettings: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/market/settings/",
                method: "GET",
                success: function (data) {
                    that.getOwnerComponent().getModel().setProperty("/settings", data);
                },
                error: function () {
                    // Use defaults
                    that.getOwnerComponent().getModel().setProperty("/settings", {
                        default_risk_pct: 1.0,
                        swing_lookback: 5,
                        alert_sound: true,
                        alert_browser: true,
                        score_weights: {}
                    });
                }
            });
        },

        _loadMT5Status: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/market/account/",
                method: "GET",
                success: function (data) {
                    var oVBox = that.byId("mt5Status");
                    if (!oVBox) return;
                    oVBox.destroyItems();

                    oVBox.addItem(new ObjectStatus({
                        text: "Connected", state: "Success", icon: "sap-icon://connected"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: "Balance: $" + (data.balance || 0).toFixed(2), state: "Information"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: "Equity: $" + (data.equity || 0).toFixed(2), state: "Information"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: "Leverage: 1:" + (data.leverage || 0), state: "Information"
                    }));
                },
                error: function () {
                    var oVBox = that.byId("mt5Status");
                    if (!oVBox) return;
                    oVBox.destroyItems();
                    oVBox.addItem(new ObjectStatus({
                        text: "MT5 Not Connected", state: "Error", icon: "sap-icon://disconnected"
                    }));
                    oVBox.addItem(new Text({
                        text: "Ensure MT5 terminal is running and logged in. Set MT5_PATH, MT5_ACCOUNT, MT5_PASSWORD, MT5_SERVER environment variables."
                    }));
                }
            });
        },

        onSaveSettings: function () {
            var that = this;
            var oSettings = this.getOwnerComponent().getModel().getProperty("/settings");

            jQuery.ajax({
                url: "/api/market/settings/",
                method: "PUT",
                contentType: "application/json",
                data: JSON.stringify(oSettings),
                success: function (data) {
                    MessageToast.show("Settings saved");
                    // Refresh model with server-validated response
                    if (data) {
                        that.getOwnerComponent().getModel().setProperty("/settings", data);
                    }
                },
                error: function () {
                    MessageToast.show("Failed to save settings");
                }
            });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("dashboard");
        }
    });
});
