sap.ui.define([], function () {
    "use strict";

    return {

        /**
         * Format price with appropriate decimal places.
         */
        formatPrice: function (fPrice, sPair) {
            if (!fPrice) return "—";
            var iDecimals = 5;
            if (sPair && (sPair.indexOf("JPY") > -1)) {
                iDecimals = 3;
            }
            if (sPair && sPair.indexOf("XAU") > -1) {
                iDecimals = 2;
            }
            return parseFloat(fPrice).toFixed(iDecimals);
        },

        /**
         * Get CSS class for trend direction.
         */
        trendClass: function (sDirection) {
            switch (sDirection) {
                case "bullish": return "trendBullish";
                case "bearish": return "trendBearish";
                default: return "trendNeutral";
            }
        },

        /**
         * Get state for ObjectStatus based on trend.
         */
        trendState: function (sDirection) {
            switch (sDirection) {
                case "bullish": return "Success";
                case "bearish": return "Error";
                default: return "Warning";
            }
        },

        /**
         * Get icon for trend direction.
         */
        trendIcon: function (sDirection) {
            switch (sDirection) {
                case "bullish": return "sap-icon://trend-up";
                case "bearish": return "sap-icon://trend-down";
                default: return "sap-icon://line-charts";
            }
        },

        /**
         * Format trade score with label.
         */
        formatTradeScore: function (iScore) {
            if (iScore === null || iScore === undefined) return "—";
            var sLabel = iScore >= 70 ? "HIGH" : iScore >= 50 ? "MEDIUM" : "LOW";
            return iScore + "/100 — " + sLabel;
        },

        /**
         * Trade score CSS class.
         */
        tradeScoreClass: function (iScore) {
            if (iScore >= 70) return "tradeScoreHigh";
            if (iScore >= 50) return "tradeScoreMedium";
            return "tradeScoreLow";
        },

        /**
         * News impact CSS class.
         */
        newsImpactClass: function (sImpact) {
            switch (sImpact) {
                case "HIGH": return "newsHigh";
                case "MEDIUM": return "newsMedium";
                default: return "newsLow";
            }
        },

        /**
         * Format time remaining until a target date.
         */
        timeRemaining: function (sTargetTime) {
            if (!sTargetTime) return "";
            var oTarget = new Date(sTargetTime);
            var oNow = new Date();
            var iDiff = oTarget - oNow;
            if (iDiff < 0) return "Passed";
            var iHours = Math.floor(iDiff / 3600000);
            var iMins = Math.floor((iDiff % 3600000) / 60000);
            return iHours + "h " + iMins + "m";
        },

        /**
         * Format win rate percentage.
         */
        formatWinRate: function (fRate) {
            if (fRate === null || fRate === undefined) return "—";
            return parseFloat(fRate).toFixed(1) + "%";
        },

        /**
         * Format PnL with color indicator.
         */
        pnlState: function (fPnl) {
            if (fPnl > 0) return "Success";
            if (fPnl < 0) return "Error";
            return "None";
        }
    };
});
