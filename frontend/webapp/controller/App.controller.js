sap.ui.define([
    "sap/ui/core/mvc/Controller"
], function (Controller) {
    "use strict";

    return Controller.extend("forex.platform.controller.App", {

        onInit: function () {
            // Request browser notification permission
            if ("Notification" in window && Notification.permission === "default") {
                Notification.requestPermission();
            }
        },

        onToggleSideNav: function () {
            var oToolPage = this.byId("toolPage");
            oToolPage.setSideExpanded(!oToolPage.getSideExpanded());
        },

        onNavItemSelect: function (oEvent) {
            var sKey = oEvent.getParameter("item").getKey();
            var oRouter = this.getOwnerComponent().getRouter();

            switch (sKey) {
                case "dashboard":
                    oRouter.navTo("dashboard");
                    break;
                case "chart":
                    var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair") || "EURUSD";
                    oRouter.navTo("chart", { pair: sPair });
                    break;
                case "journal":
                    oRouter.navTo("journal");
                    break;
                case "analytics":
                    oRouter.navTo("analytics");
                    break;
                case "settings":
                    oRouter.navTo("settings");
                    break;
            }
        }
    });
});
