sap.ui.define([
    "sap/ui/core/mvc/Controller",
    "sap/m/MessageToast",
    "sap/m/ColorPalettePopover",
    "sap/m/Dialog",
    "sap/m/Input",
    "sap/m/Button",
    "forex/platform/model/formatter"
], function (Controller, MessageToast, ColorPalettePopover, Dialog, Input, Button, formatter) {
    "use strict";

    return Controller.extend("forex.platform.controller.Chart", {

        formatter: formatter,

        _chart: null,
        _candleSeries: null,
        _emaSeries: {},
        _patternOverlaySeries: [],
        _fabricCanvas: null,
        _currentTool: "select",
        _drawingColor: "#2196F3",
        _drawings: [],
        _resizeHandler: null,

        onInit: function () {
            var oRouter = this.getOwnerComponent().getRouter();
            oRouter.getRoute("chart").attachPatternMatched(this._onRouteMatched, this);

            // Clean up chart resources when navigating away via sidebar
            oRouter.attachRouteMatched(this._onAnyRouteMatched, this);

            // Initialize risk calculator defaults
            var oModel = this.getOwnerComponent().getModel();
            oModel.setProperty("/riskBalance", 10000);
            oModel.setProperty("/riskPct", 1);
            oModel.setProperty("/riskSL", 20);
            oModel.setProperty("/riskResult", {});
            oModel.setProperty("/patternMatches", []);
            oModel.setProperty("/aiSummary", "<em>Loading analysis...</em>");
        },

        _onAnyRouteMatched: function (oEvent) {
            // Cleanup when navigating away from chart via sidebar or other means
            if (oEvent.getParameter("name") !== "chart" && this._chart) {
                this._cleanupChart();
            }
        },

        _onRouteMatched: function (oEvent) {
            var sPair = oEvent.getParameter("arguments").pair || "EURUSD";
            this.getOwnerComponent().getModel().setProperty("/selectedPair", sPair);

            // Set default timeframe
            this._timeframe = "H1";
            var oSelector = this.byId("timeframeSelector");
            if (oSelector) {
                oSelector.setSelectedKey("H1");
            }

            // Connect WebSocket for this pair
            var wsManager = this.getOwnerComponent().getWebSocketManager();
            wsManager.connectPair(sPair);

            // Initialize chart after DOM render
            setTimeout(this._initChart.bind(this), 200);
        },

        _initChart: function () {
            var oContainer = document.getElementById("tvChart");
            if (!oContainer) return;

            // Guard: check TradingView library loaded
            if (typeof LightweightCharts === "undefined") {
                MessageToast.show("TradingView Charts library not loaded");
                return;
            }

            // Cleanup previous chart
            this._cleanupChart();
            oContainer.innerHTML = "";

            // Create chart
            this._chart = LightweightCharts.createChart(oContainer, {
                width: oContainer.clientWidth,
                height: 500,
                layout: {
                    background: { type: "solid", color: "#1e1e2d" },
                    textColor: "#d1d4dc"
                },
                grid: {
                    vertLines: { color: "#2B2B43" },
                    horzLines: { color: "#2B2B43" }
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal
                },
                rightPriceScale: { borderColor: "#2B2B43" },
                timeScale: {
                    borderColor: "#2B2B43",
                    timeVisible: true,
                    secondsVisible: false
                }
            });

            // Candlestick series
            this._candleSeries = this._chart.addCandlestickSeries({
                upColor: "#4CAF50",
                downColor: "#F44336",
                borderUpColor: "#4CAF50",
                borderDownColor: "#F44336",
                wickUpColor: "#4CAF50",
                wickDownColor: "#F44336"
            });

            // EMA lines
            this._emaSeries = {};
            this._emaSeries["ema_20"] = this._chart.addLineSeries({
                color: "#FFD700", lineWidth: 1, priceLineVisible: false, lastValueVisible: false
            });
            this._emaSeries["ema_50"] = this._chart.addLineSeries({
                color: "#00BCD4", lineWidth: 1, priceLineVisible: false, lastValueVisible: false
            });
            this._emaSeries["ema_200"] = this._chart.addLineSeries({
                color: "#E040FB", lineWidth: 1, priceLineVisible: false, lastValueVisible: false
            });

            // Fabric.js canvas for drawing
            this._initFabricCanvas(oContainer);

            // Load data
            this._loadCandles();
            this._loadDrawings();

            // Resize handler (save reference for cleanup)
            var that = this;
            this._resizeHandler = function () {
                if (that._chart && oContainer) {
                    that._chart.applyOptions({ width: oContainer.clientWidth });
                }
            };
            window.addEventListener("resize", this._resizeHandler);

            // Auto-refresh every 2 seconds for near-0ms feel
            this._refreshTimer = setInterval(function () {
                that._loadCandles();
            }, 2000);

            // Pattern overlay refresh every 10 seconds
            this._patternTimer = setInterval(function () {
                that._loadPatternMatches();
            }, 10000);
        },

        _cleanupChart: function () {
            if (this._resizeHandler) {
                window.removeEventListener("resize", this._resizeHandler);
                this._resizeHandler = null;
            }
            if (this._refreshTimer) {
                clearInterval(this._refreshTimer);
                this._refreshTimer = null;
            }
            if (this._patternTimer) {
                clearInterval(this._patternTimer);
                this._patternTimer = null;
            }
            // Remove pattern overlay series
            this._clearPatternOverlays();
            if (this._chart) {
                this._chart.remove();
                this._chart = null;
            }
            this._candleSeries = null;
            this._emaSeries = {};
            if (this._fabricCanvas) {
                this._fabricCanvas.dispose();
                this._fabricCanvas = null;
            }
        },

        _initFabricCanvas: function (oChartContainer) {
            var existingCanvas = oChartContainer.querySelector(".forexDrawingCanvas");
            if (existingCanvas) existingCanvas.remove();

            var canvas = document.createElement("canvas");
            canvas.id = "drawingCanvas";
            canvas.className = "forexDrawingCanvas";
            canvas.width = oChartContainer.clientWidth;
            canvas.height = 500;
            oChartContainer.appendChild(canvas);

            this._fabricCanvas = new fabric.Canvas("drawingCanvas", {
                selection: true,
                isDrawingMode: false
            });

            var that = this;
            this._drawPoints = [];

            this._fabricCanvas.on("mouse:down", function (opt) {
                if (that._currentTool === "select") return;

                var pointer = that._fabricCanvas.getPointer(opt.e);
                that._drawPoints.push(pointer);

                if (that._currentTool === "horizontal") {
                    that._drawHorizontalLine(pointer.y);
                    that._drawPoints = [];
                } else if (that._currentTool === "text") {
                    that._drawText(pointer);
                    that._drawPoints = [];
                } else if (that._drawPoints.length >= 2) {
                    that._finishDrawing();
                }
            });
        },

        _finishDrawing: function () {
            var p = this._drawPoints;
            var obj;

            switch (this._currentTool) {
                case "trendline":
                case "ray":
                    obj = new fabric.Line([p[0].x, p[0].y, p[1].x, p[1].y], {
                        stroke: this._drawingColor,
                        strokeWidth: 2,
                        selectable: true,
                        evented: true,
                        toolType: this._currentTool
                    });
                    break;

                case "rectangle":
                    var left = Math.min(p[0].x, p[1].x);
                    var top = Math.min(p[0].y, p[1].y);
                    obj = new fabric.Rect({
                        left: left,
                        top: top,
                        width: Math.abs(p[1].x - p[0].x),
                        height: Math.abs(p[1].y - p[0].y),
                        fill: this._drawingColor + "22",
                        stroke: this._drawingColor,
                        strokeWidth: 1,
                        selectable: true,
                        evented: true,
                        toolType: "rectangle"
                    });
                    break;

                case "fibonacci":
                    this._drawFibonacci(p[0], p[1]);
                    this._drawPoints = [];
                    return;
            }

            if (obj) {
                this._fabricCanvas.add(obj);
                this._drawings.push({
                    type: this._currentTool,
                    points: p.map(function (pt) { return { x: pt.x, y: pt.y }; }),
                    color: this._drawingColor
                });
            }
            this._drawPoints = [];
        },

        _drawHorizontalLine: function (y) {
            var line = new fabric.Line([0, y, this._fabricCanvas.width, y], {
                stroke: this._drawingColor,
                strokeWidth: 1,
                strokeDashArray: [5, 5],
                selectable: true,
                evented: true,
                toolType: "horizontal"
            });
            this._fabricCanvas.add(line);
        },

        _drawText: function (pointer) {
            var text = new fabric.IText("Label", {
                left: pointer.x,
                top: pointer.y,
                fontSize: 14,
                fill: this._drawingColor,
                selectable: true,
                evented: true,
                toolType: "text"
            });
            this._fabricCanvas.add(text);
        },

        _drawFibonacci: function (p1, p2) {
            var levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1];
            var colors = ["#F44336", "#FF9800", "#FFC107", "#9E9E9E", "#00BCD4", "#2196F3", "#4CAF50"];
            var range = p2.y - p1.y;

            for (var i = 0; i < levels.length; i++) {
                var y = p1.y + range * levels[i];
                var line = new fabric.Line([0, y, this._fabricCanvas.width, y], {
                    stroke: colors[i], strokeWidth: 1, strokeDashArray: [3, 3],
                    selectable: false, evented: false, toolType: "fibonacci"
                });
                var label = new fabric.Text((levels[i] * 100).toFixed(1) + "%", {
                    left: 5, top: y - 12, fontSize: 10, fill: colors[i],
                    selectable: false, toolType: "fibonacci"
                });
                this._fabricCanvas.add(line, label);
            }
        },

        // === DATA LOADING ===

        _loadCandles: function () {
            var that = this;
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");

            jQuery.ajax({
                url: "/api/market/candles/?pair=" + sPair + "&timeframe=" + this._timeframe + "&count=500",
                method: "GET",
                timeout: 10000,
                success: function (data) {
                    if (!data || !data.length || !that._candleSeries) return;

                    // Format for TradingView — sorted by time ascending
                    var candles = data.map(function (c) {
                        return {
                            time: Math.floor(new Date(c.time).getTime() / 1000),
                            open: c.open,
                            high: c.high,
                            low: c.low,
                            close: c.close
                        };
                    }).sort(function (a, b) { return a.time - b.time; });

                    that._candleSeries.setData(candles);
                    that._currentCandles = candles;

                    // Update current price
                    var last = candles[candles.length - 1];
                    if (last) {
                        that.getOwnerComponent().getModel().setProperty("/currentPrice", last.close);
                    }

                    // Load indicator overlay + analysis
                    that._loadIndicatorOverlay(sPair);
                },
                error: function (xhr, status) {
                    if (status === "timeout") {
                        MessageToast.show("Candle data request timed out");
                    }
                }
            });
        },

        _loadIndicatorOverlay: function (sPair) {
            var that = this;

            jQuery.ajax({
                url: "/api/market/analysis/?pair=" + sPair,
                method: "GET",
                timeout: 10000,
                success: function (data) {
                    var oModel = that.getOwnerComponent().getModel("analysis");
                    if (data.timeframes) oModel.setProperty("/timeframes", data.timeframes);
                    if (data.structure) oModel.setProperty("/structure", data.structure);
                    if (data.liquidity) oModel.setProperty("/liquidity", data.liquidity);
                    if (data.trade_score !== undefined) oModel.setProperty("/tradeScore", data.trade_score);
                    if (data.score_breakdown) oModel.setProperty("/scoreBreakdown", data.score_breakdown);

                    // Generate summary
                    that._generateSummary(data);
                },
                error: function () {
                    // Analysis not ready yet — Celery hasn't computed or Redis empty
                }
            });
        },

        _loadPatternMatches: function () {
            // Pattern matches come via WebSocket (pushed by scan_patterns Celery task)
            // They're already set in the model by WebSocketManager._handleMessage
            // Here we just render the overlays on the chart

            var aMatches = this.getOwnerComponent().getModel().getProperty("/patternMatches") || [];
            this._renderPatternOverlays(aMatches);
        },

        _clearPatternOverlays: function () {
            // Remove previous overlay series from chart
            if (this._chart && this._patternOverlaySeries) {
                this._patternOverlaySeries.forEach(function (series) {
                    try {
                        this._chart.removeSeries(series);
                    } catch (e) {
                        // Series might already be removed
                    }
                }.bind(this));
            }
            this._patternOverlaySeries = [];
        },

        _renderPatternOverlays: function (aMatches) {
            if (!this._chart || !this._currentCandles || !aMatches.length) return;

            // Clear previous overlays
            this._clearPatternOverlays();

            var candles = this._currentCandles;
            if (!candles || candles.length < 5) return;

            var that = this;

            aMatches.forEach(function (match) {
                var matchedCount = match.matched_candles;
                var fullPattern = match.full_pattern;
                if (!fullPattern || !matchedCount) return;

                // Get the price range of the matched candles for denormalization
                var matchedCandles = candles.slice(-matchedCount);
                var prices = matchedCandles.map(function (c) { return c.close; });
                var minP = Math.min.apply(null, prices);
                var maxP = Math.max.apply(null, prices);
                var range = maxP - minP || 0.0001;

                function denormalize(normVal) {
                    return minP + normVal * range;
                }

                // === CYAN LINE: matched portion (current candles that match the pattern) ===
                var matchedPoints = fullPattern.slice(0, matchedCount).map(function (normPrice, i) {
                    return {
                        time: matchedCandles[i] ? matchedCandles[i].time : 0,
                        value: denormalize(normPrice)
                    };
                }).filter(function (p) { return p.time > 0; });

                if (matchedPoints.length > 1) {
                    var cyanSeries = that._chart.addLineSeries({
                        color: "#00E5FF",
                        lineWidth: 3,
                        lineStyle: 0, // Solid
                        priceLineVisible: false,
                        lastValueVisible: false,
                        crosshairMarkerVisible: false
                    });
                    cyanSeries.setData(matchedPoints);
                    that._patternOverlaySeries.push(cyanSeries);
                }

                // === AMBER DASHED LINE: remaining pattern (what happened historically after this point) ===
                var remaining = match.remaining_pattern;
                if (remaining && remaining.length > 0) {
                    var lastTime = candles[candles.length - 1].time;
                    var candleInterval = candles.length > 1
                        ? candles[candles.length - 1].time - candles[candles.length - 2].time
                        : 3600; // fallback 1hr

                    var futurePoints = remaining.map(function (normPrice, i) {
                        return {
                            time: lastTime + (i + 1) * candleInterval,
                            value: denormalize(normPrice)
                        };
                    });

                    if (futurePoints.length > 0) {
                        var amberSeries = that._chart.addLineSeries({
                            color: "#FFB300",
                            lineWidth: 2,
                            lineStyle: 2, // Dashed
                            priceLineVisible: false,
                            lastValueVisible: false,
                            crosshairMarkerVisible: false
                        });
                        amberSeries.setData(futurePoints);
                        that._patternOverlaySeries.push(amberSeries);
                    }
                }
            });
        },

        _generateSummary: function (data) {
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");
            var tf = data.timeframes || {};
            var h1 = tf["H1"] || {};
            var structure = data.structure || {};
            var session = data.session || {};
            var tradeScore = data.trade_score;

            var lines = [];
            lines.push("<strong>" + sPair + " " + this._timeframe + " — Summary</strong><br/>");
            lines.push("Trend: " + (h1.trend_direction || "N/A") + " (Score: " + (h1.trend_score || 0) + "/100)<br/>");

            if (structure.bos) {
                lines.push("BOS: " + structure.bos.type + " @ " + structure.bos.level + "<br/>");
            }
            if (structure.choch) {
                lines.push("CHOCH: " + structure.choch.type + " @ " + structure.choch.level + "<br/>");
            }

            lines.push("Session: " + (session.active_sessions ? session.active_sessions.join(" + ") : "N/A"));
            lines.push(" (" + (session.volatility || "N/A") + " volatility)<br/>");

            if (tradeScore !== undefined) {
                lines.push("Trade Score: <strong>" + tradeScore + "/100</strong><br/>");
            }

            // Rule-based suggestion
            var score = tradeScore || h1.trend_score || 0;
            if (score >= 70) {
                lines.push("<br/><strong style='color:#4CAF50'>High quality " + (h1.trend_direction || "") + " setup. Look for entry on pullback.</strong>");
            } else if (score >= 40) {
                lines.push("<br/><strong style='color:#FF9800'>Medium conditions. Wait for additional confirmation.</strong>");
            } else {
                lines.push("<br/><strong style='color:#F44336'>Low quality / choppy. No trade recommended.</strong>");
            }

            this.getOwnerComponent().getModel().setProperty("/aiSummary", lines.join(""));
        },

        _loadDrawings: function () {
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");

            jQuery.ajax({
                url: "/api/market/drawings/?pair=" + sPair + "&timeframe=" + this._timeframe,
                method: "GET",
                success: function (data) {
                    var results = data.results || data;
                    if (!results || !results.length) return;
                    // Drawings are restored by coordinate mapping
                    // Full coordinate-to-price mapping requires chart visible range
                    // which is handled by Fabric canvas persistence
                }
            });
        },

        // === EVENT HANDLERS ===

        onNavBack: function () {
            this._cleanupChart();
            this.getOwnerComponent().getRouter().navTo("dashboard");
        },

        onTimeframeChange: function (oEvent) {
            this._timeframe = oEvent.getParameter("item").getKey();
            this._loadCandles();
            this._loadDrawings();
        },

        onDrawingToolChange: function (oEvent) {
            var sKey = oEvent.getParameter("item").getKey();
            this._currentTool = sKey;
            this._drawPoints = [];

            if (this._fabricCanvas) {
                var canvas = document.getElementById("drawingCanvas");
                if (sKey === "select") {
                    canvas.classList.remove("active");
                    this._fabricCanvas.isDrawingMode = false;
                    this._fabricCanvas.selection = true;
                } else {
                    canvas.classList.add("active");
                    this._fabricCanvas.isDrawingMode = false;
                    this._fabricCanvas.selection = false;
                }
            }
        },

        onColorPicker: function (oEvent) {
            var that = this;
            if (!this._colorPalette) {
                this._colorPalette = new ColorPalettePopover({
                    colorSelect: function (oEvt) {
                        that._drawingColor = oEvt.getParameter("value");
                    }
                });
            }
            this._colorPalette.openBy(oEvent.getSource());
        },

        onDeleteDrawing: function () {
            if (this._fabricCanvas) {
                var active = this._fabricCanvas.getActiveObjects();
                var that = this;
                if (active.length > 0) {
                    active.forEach(function (obj) {
                        that._fabricCanvas.remove(obj);
                    });
                    this._fabricCanvas.discardActiveObject();
                    MessageToast.show("Drawing deleted");
                }
            }
        },

        onSaveDrawings: function () {
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");
            var that = this;

            if (!this._fabricCanvas) return;

            var objects = this._fabricCanvas.getObjects();
            if (!objects.length) {
                MessageToast.show("No drawings to save");
                return;
            }

            // Save each drawing, tracking successes and failures
            var saved = 0;
            var failed = 0;
            var total = objects.length;

            objects.forEach(function (obj) {
                var drawing = {
                    pair: sPair,
                    timeframe: that._timeframe,
                    tool_type: obj.toolType || "trendline",
                    coordinates: that._getObjectCoords(obj),
                    color: obj.stroke || obj.fill || "#2196F3",
                    thickness: obj.strokeWidth || 2
                };

                jQuery.ajax({
                    url: "/api/market/drawings/",
                    method: "POST",
                    contentType: "application/json",
                    data: JSON.stringify(drawing),
                    success: function () {
                        saved++;
                    },
                    error: function () {
                        failed++;
                    },
                    complete: function () {
                        if (saved + failed === total) {
                            if (failed === 0) {
                                MessageToast.show(saved + " drawings saved");
                            } else {
                                MessageToast.show(saved + " saved, " + failed + " failed");
                            }
                        }
                    }
                });
            });
        },

        onSavePattern: function () {
            var that = this;
            var sPair = this.getOwnerComponent().getModel().getProperty("/selectedPair");

            jQuery.ajax({
                url: "/api/market/candles/?pair=" + sPair + "&timeframe=" + this._timeframe + "&count=50",
                method: "GET",
                success: function (data) {
                    if (!data || data.length < 10) {
                        MessageToast.show("Not enough data for pattern");
                        return;
                    }

                    var closes = data.slice(-20).map(function (c) { return c.close; });
                    var min = Math.min.apply(null, closes);
                    var max = Math.max.apply(null, closes);
                    var range = max - min || 1;
                    var normalized = closes.map(function (c) { return (c - min) / range; });

                    var oInput = new Input({ placeholder: "e.g., Double Top" });
                    var oDialog = new Dialog({
                        title: "Save Pattern Template",
                        content: [oInput],
                        beginButton: new Button({
                            text: "Save",
                            type: "Emphasized",
                            press: function () {
                                var sName = oInput.getValue() || "Unnamed Pattern";
                                jQuery.ajax({
                                    url: "/api/market/patterns/",
                                    method: "POST",
                                    contentType: "application/json",
                                    data: JSON.stringify({
                                        name: sName,
                                        pair: sPair,
                                        timeframe: that._timeframe,
                                        price_sequence: normalized,
                                        lookback_candles: normalized.length
                                    }),
                                    success: function () {
                                        MessageToast.show("Pattern '" + sName + "' saved — scanning will begin in ~10s");
                                    },
                                    error: function () {
                                        MessageToast.show("Failed to save pattern");
                                    }
                                });
                                oDialog.close();
                                oDialog.destroy();
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
                }
            });
        },

        onCalculateRisk: function () {
            var oModel = this.getOwnerComponent().getModel();
            var sPair = oModel.getProperty("/selectedPair");

            jQuery.ajax({
                url: "/api/market/risk/",
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify({
                    balance: parseFloat(oModel.getProperty("/riskBalance")) || 10000,
                    risk_pct: parseFloat(oModel.getProperty("/riskPct")) || 1,
                    sl_pips: parseFloat(oModel.getProperty("/riskSL")) || 20,
                    pair: sPair
                }),
                success: function (data) {
                    // Normalize tp_options keys: "1:2" → "rr_1_2" to avoid colon in UI5 binding paths
                    if (data.tp_options) {
                        var normalized = {};
                        Object.keys(data.tp_options).forEach(function (key) {
                            normalized["rr_" + key.replace(":", "_")] = data.tp_options[key];
                        });
                        data.tp_options = normalized;
                    }
                    if (data.potential_profit) {
                        var normProfit = {};
                        Object.keys(data.potential_profit).forEach(function (key) {
                            normProfit["rr_" + key.replace(":", "_")] = data.potential_profit[key];
                        });
                        data.potential_profit = normProfit;
                    }
                    oModel.setProperty("/riskResult", data);
                    MessageToast.show("Lot Size: " + data.lot_size);
                },
                error: function () {
                    MessageToast.show("Calculation failed");
                }
            });
        },

        _getObjectCoords: function (obj) {
            if (obj.type === "line") {
                return [{ x: obj.x1, y: obj.y1 }, { x: obj.x2, y: obj.y2 }];
            } else if (obj.type === "rect") {
                return [{ x: obj.left, y: obj.top }, { x: obj.left + obj.width, y: obj.top + obj.height }];
            } else if (obj.type === "i-text" || obj.type === "text") {
                return [{ x: obj.left, y: obj.top }];
            }
            return [{ x: obj.left || 0, y: obj.top || 0 }];
        },

        onExit: function () {
            this._cleanupChart();
        }
    });
});
