/** @odoo-module */

import { registry } from "@web/core/registry";
import { loadJS } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

import { Component, onWillStart, useRef, onMounted, useState } from "@odoo/owl";

//  Top 5 Customer all charts

// Bar chart
export class VehicleChartRendorBar extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.state = useState({ timeFilter: "daily" });

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order",
            domain,
            ["partner_id"],
            ["partner_id"],
            { limit: 5, orderby: "partner_id_count desc" }
        );

        const labels = groups.map(g => g.partner_id ? g.partner_id[1] : 'Unknown');
        const data = groups.map(g => g.partner_id_count);

        const backgroundColors = ["#FFB6C1", "#D8BFD8", "#87CEFA", "#FFFFE0", "#ADD8E6"];

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.chartRef.el, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Customers",
                    data,
                    backgroundColor: backgroundColors,
                    hoverBackgroundColor: backgroundColors
                }],
            },
            options: { responsive: true },
        });
    }
}

// Doughnut chart
export class VehicleChartRendordoughnut extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        this.state = useState({ timeFilter: "daily" });

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order",
            domain,
            ["partner_id"],
            ["partner_id"],
            { limit: 5, orderby: "partner_id_count desc" }
        );

        const labels = groups.map(g => g.partner_id ? g.partner_id[1] : 'Unknown');
        const data = groups.map(g => g.partner_id_count);

        const backgroundColors = ["#FFB6C1", "#D8BFD8", "#87CEFA", "#FFFFE0", "#ADD8E6"];

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.chartRef.el, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Customers",
                    data,
                    backgroundColor: backgroundColors,
                }],
            },
            options: { responsive: true },
        });
    }
}

// pie chart 
export class VehicleChartRendorpie extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        this.state = useState({ timeFilter: "daily" });
        this.actionService = useService("action");

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order",
            domain,
            ["partner_id"],
            ["partner_id"],
            { limit: 5, orderby: "partner_id_count desc" }
        );

        const labels = groups.map(g => g.partner_id ? g.partner_id[1] : 'Unknown');
        const data = groups.map(g => g.partner_id_count);

        const backgroundColors = ["#FFB6C1", "#D8BFD8", "#87CEFA", "#FFFFE0", "#ADD8E6"];

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.chartRef.el, {
            type: "pie",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Customers",
                    data,
                    backgroundColor: backgroundColors,
                }],
            },
            options: { responsive: true },
        });
    }
}

// line chart
export class VehicleChartRendorline extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        this.state = useState({ timeFilter: "daily" });

        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order",
            domain,
            ["partner_id"],
            ["partner_id"],
            { limit: 5, orderby: "partner_id_count desc" }
        );

        const labels = groups.map(g => g.partner_id ? g.partner_id[1] : 'Unknown');
        const data = groups.map(g => g.partner_id_count);

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.chartRef.el, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Customers",
                    data,
                    borderColor: "#CDA0E6",
                    fill: false,
                }],
            },
            options: { responsive: true },
        });
    }
}

VehicleChartRendorBar.template = "owl.VehicleChartRendorBar";
VehicleChartRendorpie.template = "owl.VehicleChartRendorpie";
VehicleChartRendorline.template = "owl.VehicleChartRendorline";
VehicleChartRendordoughnut.template = "owl.VehicleChartRendordoughnut";

// Top 5 products all charts

// line chart
export class ProductLine extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order.line",
            domain,
            ["product_id"],
            ["product_id"],
            { limit: 5, orderby: "product_id_count desc" }
        );

        const labels = groups.map(g => g.product_id ? g.product_id[1] : 'Unknown');
        const data = groups.map(g => g.product_id_count);

        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = this.chartRef.el.getContext("2d");
        this.chart = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Products Sales",
                    data,
                    backgroundColor: "rgba(0, 0, 255, 0.2)",
                    fill: false
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
}

// ProductBar chart
export class ProductBar extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order.line",
            domain,
            ["product_id"],
            ["product_id"],
            { limit: 5, orderby: "product_id_count desc" }
        );

        const labels = groups.map(g => g.product_id ? g.product_id[1] : 'Unknown');
        const data = groups.map(g => g.product_id_count);

        const backgroundColors = [
            "rgba(255, 182, 193, 0.5)",
            "rgba(216, 191, 216, 0.5)",
            "rgba(135, 206, 250, 0.5)",
            "rgba(255, 255, 224, 0.5)",
            "rgba(173, 216, 230, 0.5)"
        ];

        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = this.chartRef.el.getContext("2d");
        this.chart = new Chart(ctx, {
            type: "bar",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Products Sales",
                    data,
                    backgroundColor: backgroundColors.slice(0, data.length),
                    hoverBackgroundColor: backgroundColors
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { beginAtZero: true }
                }
            }
        });
    }
}

// Productpie chart
export class Productpie extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order.line",
            domain,
            ["product_id"],
            ["product_id"],
            { limit: 5, orderby: "product_id_count desc" }
        );

        const labels = groups.map(g => g.product_id ? g.product_id[1] : 'Unknown');
        const data = groups.map(g => g.product_id_count);

        const backgroundColors = [
            "rgba(255, 182, 193, 0.5)",
            "rgba(216, 191, 216, 0.5)",
            "rgba(135, 206, 250, 0.5)",
            "rgba(255, 255, 224, 0.5)",
            "rgba(173, 216, 230, 0.5)"
        ].slice(0, data.length);

        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = this.chartRef.el.getContext("2d");
        this.chart = new Chart(ctx, {
            type: "pie",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Products Sales",
                    data,
                    backgroundColor: backgroundColors,
                    borderColor: "rgba(0, 0, 0, 0.8)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false
            }
        });
    }
}

// Productdoughnut chart
export class Productdoughnut extends Component {
    setup() {
        this.chartRef = useRef("chart");
        this.orm = useService("orm");
        onWillStart(async () => {
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.3.0/chart.umd.min.js");
        });

        onMounted(async () => await this.renderChart());
    }

    async renderChart() {
        const domain = this.props.domain || [];
        const groups = await this.orm.readGroup(
            "sale.order.line",
            domain,
            ["product_id"],
            ["product_id"],
            { limit: 5, orderby: "product_id_count desc" }
        );

        const labels = groups.map(g => g.product_id ? g.product_id[1] : 'Unknown');
        const data = groups.map(g => g.product_id_count);

        const backgroundColors = [
            "rgba(255, 182, 193, 0.5)",
            "rgba(216, 191, 216, 0.5)",
            "rgba(135, 206, 250, 0.5)",
            "rgba(255, 255, 224, 0.5)",
            "rgba(173, 216, 230, 0.5)"
        ].slice(0, data.length);

        if (this.chart) {
            this.chart.destroy();
        }

        const ctx = this.chartRef.el.getContext("2d");
        this.chart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels,
                datasets: [{
                    label: "Top 5 Products Sales",
                    data,
                    backgroundColor: backgroundColors,
                    borderColor: "rgba(0, 0, 0, 0.8)",
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true
            }
        });
    }
}

ProductLine.template = "owl.ProductLine";
ProductBar.template = "owl.ProductBar";
Productpie.template = "owl.Productpie";
Productdoughnut.template = "owl.Productdoughnut";