/** @odoo-module **/

import { Component, onWillStart, useEffect, useRef } from "@odoo/owl";
import { loadBundle } from "@web/core/assets";

/**
 * Interactive Chart.js wrapper (animation, tooltip, clickable legend).
 */
export class PlChart extends Component {
    static template = "vpk_hospital_balance_sheet.PlChart";
    static props = {
        type: String,
        labels: { type: Array, optional: true },
        datasets: { type: Array, optional: true },
        height: { type: Number, optional: true },
        centerText: { type: String, optional: true },
        onClickItem: { type: Function, optional: true },
        stacked: { type: Boolean, optional: true },
        horizontal: { type: Boolean, optional: true },
        className: { type: String, optional: true },
    };
    static defaultProps = {
        labels: [],
        datasets: [],
        height: 260,
        stacked: false,
        horizontal: false,
        className: "",
    };

    setup() {
        this.canvasRef = useRef("canvas");
        this.chart = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        useEffect(
            () => {
                this.renderChart();
                return () => {
                    if (this.chart) {
                        this.chart.destroy();
                        this.chart = null;
                    }
                };
            },
            () => [
                this.props.type,
                JSON.stringify(this.props.labels || []),
                JSON.stringify(this.props.datasets || []),
                this.props.height,
                this.props.centerText || "",
                this.props.horizontal,
                this.props.stacked,
            ]
        );
    }

    renderChart() {
        const canvas = this.canvasRef.el;
        if (!canvas || typeof Chart === "undefined") {
            return;
        }
        if (this.chart) {
            this.chart.destroy();
            this.chart = null;
        }
        const config = this.getConfig();
        this.chart = new Chart(canvas, config);
        // Canvas text does not re-render when the web font finishes loading
        document.fonts.ready.then(() => this.chart?.update("none"));
    }

    getConfig() {
        const type = this.props.horizontal ? "bar" : this.props.type;
        const datasets = (this.props.datasets || []).map((ds) => ({
            ...ds,
            borderWidth: ds.borderWidth ?? (type === "line" ? 2.5 : 0),
            tension: ds.tension ?? (type === "line" ? 0.35 : 0),
            fill: ds.fill ?? false,
            pointRadius: ds.pointRadius ?? (type === "line" ? 3 : 0),
            pointHoverRadius: ds.pointHoverRadius ?? 5,
            borderRadius: ds.borderRadius ?? (type === "bar" ? 4 : 0),
            maxBarThickness: ds.maxBarThickness ?? 36,
        }));

        const self = this;
        const isDonut = type === "doughnut" || type === "pie";
        const family = getComputedStyle(this.canvasRef.el).fontFamily || "sans-serif";

        const plugins = {
            legend: {
                display: true,
                position: isDonut ? "right" : "bottom",
                labels: {
                    boxWidth: 12,
                    boxHeight: 12,
                    usePointStyle: true,
                    pointStyle: "rectRounded",
                    padding: 14,
                    font: { size: 12, family },
                    color: "#5b6b65",
                },
            },
            tooltip: {
                enabled: true,
                backgroundColor: "#1a2e28",
                titleFont: { size: 12, family },
                bodyFont: { size: 12, family },
                padding: 10,
                cornerRadius: 8,
                callbacks: {
                    label(ctx) {
                        const label = ctx.dataset.label || ctx.label || "";
                        const value = ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed ?? 0;
                        const num = typeof value === "object" ? value.y ?? value.x ?? 0 : value;
                        const formatted = new Intl.NumberFormat("th-TH", {
                            minimumFractionDigits: 1,
                            maximumFractionDigits: 1,
                        }).format(num);
                        if (isDonut) {
                            const data = ctx.dataset.data || [];
                            const total = data.reduce((a, b) => a + Math.abs(b || 0), 0) || 1;
                            const pct = ((Math.abs(num) / total) * 100).toFixed(1);
                            return `${label}: ${formatted} ลบ. (${pct}%)`;
                        }
                        return `${label}: ${formatted} ลบ.`;
                    },
                },
            },
        };

        if (isDonut && this.props.centerText) {
            plugins.plCenterText = {
                text: this.props.centerText,
            };
        }

        const scales = isDonut
            ? {}
            : {
                  x: {
                      stacked: this.props.stacked,
                      grid: { display: !this.props.horizontal, color: "#eef2f0" },
                      ticks: {
                          color: "#6b7a74",
                          font: { size: 11, family },
                      },
                  },
                  y: {
                      stacked: this.props.stacked,
                      beginAtZero: true,
                      grid: { color: "#eef2f0" },
                      ticks: {
                          color: "#6b7a74",
                          font: { size: 11, family },
                          callback(value) {
                              return new Intl.NumberFormat("th-TH", {
                                  maximumFractionDigits: 1,
                              }).format(value);
                          },
                      },
                  },
              };

        if (this.props.horizontal) {
            scales.x.beginAtZero = true;
            scales.indexAxis = undefined;
        }

        return {
            type,
            data: {
                labels: this.props.labels || [],
                datasets,
            },
            options: {
                cutout: isDonut ? "58%" : undefined,
                indexAxis: this.props.horizontal ? "y" : "x",
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 900,
                    easing: "easeOutQuart",
                },
                animations: {
                    colors: { duration: 700 },
                    numbers: { duration: 900, easing: "easeOutQuart" },
                },
                hover: {
                    mode: isDonut ? "nearest" : "index",
                    intersect: isDonut,
                    animationDuration: 200,
                },
                interaction: {
                    mode: isDonut ? "nearest" : "index",
                    intersect: isDonut,
                },
                onClick(evt, elements) {
                    if (!self.props.onClickItem || !elements.length) {
                        return;
                    }
                    const el = elements[0];
                    self.props.onClickItem({
                        datasetIndex: el.datasetIndex,
                        index: el.index,
                        label: (self.props.labels || [])[el.index],
                        value: (self.props.datasets?.[el.datasetIndex]?.data || [])[el.index],
                    });
                },
                plugins,
                scales,
            },
            plugins: isDonut
                ? [
                      {
                          id: "plCenterText",
                          afterDraw(chart) {
                              const text = chart.options.plugins?.plCenterText?.text;
                              if (!text) {
                                  return;
                              }
                              const { ctx, chartArea } = chart;
                              if (!chartArea) {
                                  return;
                              }
                              const cx = (chartArea.left + chartArea.right) / 2;
                              const cy = (chartArea.top + chartArea.bottom) / 2;
                              ctx.save();
                              ctx.textAlign = "center";
                              ctx.textBaseline = "middle";
                              ctx.fillStyle = "#1a2e28";
                              ctx.font = `700 16px ${getComputedStyle(chart.canvas).fontFamily}`;
                              const lines = String(text).split("\n");
                              lines.forEach((line, i) => {
                                  const y = cy + (i - (lines.length - 1) / 2) * 18;
                                  if (i === lines.length - 1 && lines.length > 1) {
                                      ctx.fillStyle = "#6b7a74";
                                      ctx.font = `12px ${getComputedStyle(chart.canvas).fontFamily}`;
                                  }
                                  ctx.fillText(line, cx, y);
                              });
                              ctx.restore();
                          },
                      },
                  ]
                : [],
        };
    }
}
