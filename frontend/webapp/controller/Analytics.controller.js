sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/Text",
    "sap/m/ObjectStatus",
    "forex/platform/model/formatter"
], function (Controller, Text, ObjectStatus, formatter) {
    "use strict";

    return Controller.extend("forex.platform.controller.Analytics", {

        formatter: formatter,

        onInit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            oRouter.getRoute("analytics").attachPatternMatched(this._onRouteMatched, this);
        },

        _onRouteMatched: function () {
            this._loadAnalytics();
            this._loadScoreValidation();
        },

        _loadAnalytics: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/journal/analytics/",
                method: "GET",
                success: function (data) {
                    var oModel = that.getOwnerComponent().getModel("journal");
                    oModel.setProperty("/analytics", data);

                    // Transform pair win rates for table
                    var aPairs = [];
                    if (data.pair_win_rates) {
                        Object.keys(data.pair_win_rates).forEach(function (pair) {
                            aPairs.push({
                                pair: pair,
                                winRate: Math.round(data.pair_win_rates[pair] * 10) / 10
                            });
                        });
                    }
                    oModel.setProperty("/pairWinRates", aPairs);

                    // Transform monthly PnL for table
                    var aMonths = [];
                    if (data.monthly_pnl) {
                        Object.keys(data.monthly_pnl).sort().forEach(function (month) {
                            aMonths.push({
                                month: month,
                                pnl: Math.round(data.monthly_pnl[month] * 100) / 100
                            });
                        });
                    }
                    oModel.setProperty("/monthlyPnl", aMonths);
                },
                error: function () {
                    // Not enough trades yet
                }
            });
        },

        _loadScoreValidation: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/journal/score-validation/",
                method: "GET",
                success: function (data) {
                    var oVBox = that.byId("scoreValidation");
                    if (!oVBox) return;

                    oVBox.destroyItems();

                    if (data.message) {
                        oVBox.addItem(new Text({ text: data.message }));
                        return;
                    }

                    oVBox.addItem(new ObjectStatus({
                        text: "Total Scored Trades: " + data.total_scored_trades,
                        state: "Information"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: "High Score (70+) Win Rate: " + data.high_score_win_rate + "%",
                        state: data.high_score_win_rate >= 50 ? "Success" : "Error"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: "Low Score (<70) Win Rate: " + data.low_score_win_rate + "%",
                        state: data.low_score_win_rate >= 50 ? "Success" : "Error"
                    }));
                    oVBox.addItem(new ObjectStatus({
                        text: data.score_adds_value ? "Score system IS adding value" : "Score system needs adjustment",
                        state: data.score_adds_value ? "Success" : "Warning",
                        icon: data.score_adds_value ? "sap-icon://accept" : "sap-icon://alert"
                    }));
                },
                error: function () {
                    var oVBox = that.byId("scoreValidation");
                    if (oVBox) {
                        oVBox.destroyItems();
                        oVBox.addItem(new Text({ text: "Need at least 30 scored trades for validation." }));
                    }
                }
            });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("dashboard");
        }
    });
});
