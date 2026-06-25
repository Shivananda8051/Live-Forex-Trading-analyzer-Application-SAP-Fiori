sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/MessageToast",
    "sap/m/Dialog",
    "sap/m/Input",
    "sap/m/Select",
    "sap/ui/core/Item",
    "sap/m/Button",
    "sap/m/Label",
    "sap/ui/layout/form/SimpleForm",
    "sap/ui/model/Filter",
    "sap/ui/model/FilterOperator",
    "forex/platform/model/formatter"
], function (Controller, MessageToast, Dialog, Input, Select, Item, Button, Label, SimpleForm, Filter, FilterOperator, formatter) {
    "use strict";

    return Controller.extend("forex.platform.controller.Journal", {

        formatter: formatter,

        onInit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            oRouter.getRoute("journal").attachPatternMatched(this._onRouteMatched, this);
        },

        _onRouteMatched: function () {
            this._loadTrades();
            this._loadAnalytics();
        },

        _loadTrades: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/journal/trades/",
                method: "GET",
                success: function (data) {
                    var trades = data.results || data;
                    that.getOwnerComponent().getModel("journal").setProperty("/trades", trades);
                },
                error: function () {
                    that.getOwnerComponent().getModel("journal").setProperty("/trades", []);
                }
            });
        },

        _loadAnalytics: function () {
            var that = this;
            jQuery.ajax({
                url: "/api/journal/analytics/",
                method: "GET",
                success: function (data) {
                    that.getOwnerComponent().getModel("journal").setProperty("/analytics", data);
                },
                error: function () {
                    // Not enough trades yet
                }
            });
        },

        onNavBack: function () {
            this.getOwnerComponent().getRouter().navTo("dashboard");
        },

        onAddTrade: function () {
            var that = this;
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair") || "EURUSD";

            var oPairInput = new Input({ value: sPair });
            var oDirSelect = new Select({
                items: [
                    new Item({ key: "BUY", text: "BUY" }),
                    new Item({ key: "SELL", text: "SELL" })
                ]
            });
            var oEntry = new Input({ type: "Number", placeholder: "Entry Price" });
            var oSL = new Input({ type: "Number", placeholder: "SL Price" });
            var oTP = new Input({ type: "Number", placeholder: "TP Price" });
            var oLots = new Input({ type: "Number", placeholder: "Lot Size", value: "0.01" });
            var oNotes = new Input({ placeholder: "Notes (optional)" });

            var oDialog = new Dialog({
                title: "Log New Trade",
                content: [
                    new SimpleForm({
                        editable: true,
                        content: [
                            new Label({ text: "Pair" }), oPairInput,
                            new Label({ text: "Direction" }), oDirSelect,
                            new Label({ text: "Entry Price" }), oEntry,
                            new Label({ text: "Stop Loss" }), oSL,
                            new Label({ text: "Take Profit" }), oTP,
                            new Label({ text: "Lot Size" }), oLots,
                            new Label({ text: "Notes" }), oNotes
                        ]
                    })
                ],
                beginButton: new Button({
                    text: "Save",
                    type: "Emphasized",
                    press: function () {
                        var oData = {
                            pair: oPairInput.getValue(),
                            direction: oDirSelect.getSelectedKey(),
                            entry_price: parseFloat(oEntry.getValue()),
                            sl_price: parseFloat(oSL.getValue()),
                            tp_price: parseFloat(oTP.getValue()),
                            lot_size: parseFloat(oLots.getValue()),
                            notes: oNotes.getValue(),
                            result: "OPEN"
                        };

                        jQuery.ajax({
                            url: "/api/journal/trades/",
                            method: "POST",
                            contentType: "application/json",
                            data: JSON.stringify(oData),
                            success: function () {
                                MessageToast.show("Trade logged");
                                that._loadTrades();
                                that._loadAnalytics();
                            },
                            error: function () {
                                MessageToast.show("Failed to save trade");
                            },
                            complete: function () {
                                oDialog.close();
                                oDialog.destroy();
                            }
                        });
                    }
                }),
                endButton: new Button({
                    text: "Cancel",
                    press: function () {
                        oDialog.close();
                        oDialog.destroy();
                    }
                })
            });

            oDialog.open();
        },

        onTradePress: function (oEvent) {
            var oContext = oEvent.getSource().getBindingContext("journal");
            if (oContext) {
                var oTrade = oContext.getObject();
                MessageToast.show(oTrade.pair + " " + oTrade.direction + " — " + oTrade.result);
            }
        },

        onFilterTrades: function (oEvent) {
            var sQuery = oEvent.getParameter("newValue").toUpperCase();
            var oTable = this.byId("tradesTable");
            var oBinding = oTable.getBinding("items");
            if (sQuery) {
                oBinding.filter([
                    new Filter("pair", FilterOperator.Contains, sQuery)
                ]);
            } else {
                oBinding.filter([]);
            }
        }
    });
});
