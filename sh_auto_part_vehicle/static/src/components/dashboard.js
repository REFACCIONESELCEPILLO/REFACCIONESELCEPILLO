import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { VehiclesCardall, VehiclesModel, VehiclesMake, VehiclesBrand, VehiclesQuotations, VehiclesSales, Invoices, Overdue } from "./vehicles_card"
import { VehicleChartRendorBar, VehicleChartRendorline, VehicleChartRendorpie, VehicleChartRendordoughnut, ProductBar, Productpie, Productdoughnut } from "./chart_render";
import { ProductLine } from "./chart_render"

export class VehicleDashboard extends Component {
    setup() {
        const savedFilter = localStorage.getItem('salesFilter');
        this.state = useState({
            totalBrands: 0,
            totalMakes: 0,
            totalModels: 0,
            totalMotorcycles: 0,
            totalQuotations: 0,
            totalSales: 0,
            totalInvoices: 0,
            overdue: 0,
            startDate: null,
            endDate: null,
            chartType: "bar",
            productcharttype: "line",
            custom: savedFilter || 'daily',
            custom: localStorage.getItem("salesFilter") || "none",
            startDate: localStorage.getItem("salesStartDate") || null,
            endDate: localStorage.getItem("salesEndDate") || null,

        });

        if (this.state.startDate && this.state.endDate) {
            this.state.custom = "";
            this.getVehicleCounts();
        }


        this.orm = useService("orm");
        this.actionService = useService("action")

        onWillStart(async () => {
            await this.getVehicleCounts();
        });
    }

     
   
    




    // getCurrentDomain() {
    //     let domain = [];

    //     // Apply date range filter
    //     if (this.state.startDate && this.state.endDate) {
    //         domain.push(["create_date", ">=", this.state.startDate]);
    //         domain.push(["create_date", "<=", this.state.endDate]);
    //     }
    //     // Apply custom filters (daily, weekly, monthly)
    //     else if (this.state.custom) {
    //         const today = new Date();
    //         let startDate, endDate;

    //         if (this.state.custom === "daily") {
    //             startDate = today.toISOString().split("T")[0];
    //             endDate = today.toISOString().split("T")[0];
    //         }
    //         else if (this.state.custom === "weekly") {
    //             const firstDayOfWeek = new Date(today);
    //             firstDayOfWeek.setDate(today.getDate() - today.getDay());
    //             startDate = firstDayOfWeek.toISOString().split("T")[0];
    //             endDate = today.toISOString().split("T")[0];
    //         }
    //         else if (this.state.custom === "monthly") {
    //             const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    //             startDate = firstDayOfMonth.toISOString().split("T")[0];
    //             endDate = today.toISOString().split("T")[0];
    //         }

    //         domain.push(["create_date", ">=", startDate]);
    //         domain.push(["create_date", "<=", endDate]);
    //     }

    //     return domain;
    // }

    getCurrentDomain() {
        let domain = [];
    
        // If custom is 'none', skip all filters
        if (this.state.custom === "none") {
            return domain;
        }
    
        // Apply date range filter
        if (this.state.startDate && this.state.endDate) {
            domain.push(["create_date", ">=", this.state.startDate]);
            domain.push(["create_date", "<=", this.state.endDate]);
        }
        // Apply custom filters (daily, weekly, monthly)
        else if (this.state.custom) {
            const today = new Date();
            let startDate, endDate;
    
            if (this.state.custom === "daily") {
                startDate = today.toISOString().split("T")[0];
                endDate = today.toISOString().split("T")[0];
            }
            else if (this.state.custom === "weekly") {
                const firstDayOfWeek = new Date(today);
                firstDayOfWeek.setDate(today.getDate() - today.getDay());
                startDate = firstDayOfWeek.toISOString().split("T")[0];
                endDate = today.toISOString().split("T")[0];
            }
            else if (this.state.custom === "monthly") {
                const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
                startDate = firstDayOfMonth.toISOString().split("T")[0];
                endDate = today.toISOString().split("T")[0];
            }
    
            domain.push(["create_date", ">=", startDate]);
            domain.push(["create_date", "<=", endDate]);
        }
    
        return domain;
    }
    

    async getVehicleCounts() {
        try {
            let domain = [];
    
            // If filter is not "none", apply filters
            if (this.state.custom !== "none") {
                // Priority: Date Range Filter
                if (this.state.startDate && this.state.endDate) {
                    domain.push(["create_date", ">=", this.state.startDate]);
                    domain.push(["create_date", "<=", this.state.endDate]);
                }
                // Else: Daily, Weekly, Monthly
                else if (this.state.custom) {
                    const today = new Date();
                    let startDate, endDate;
    
                    if (this.state.custom === "daily") {
                        startDate = endDate = today.toISOString().split("T")[0];
                    } else if (this.state.custom === "weekly") {
                        const firstDay = new Date(today);
                        firstDay.setDate(today.getDate() - today.getDay());
                        startDate = firstDay.toISOString().split("T")[0];
                        endDate = today.toISOString().split("T")[0];
                    } else if (this.state.custom === "monthly") {
                        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
                        startDate = firstDay.toISOString().split("T")[0];
                        endDate = today.toISOString().split("T")[0];
                    }
    
                    domain.push(["create_date", ">=", startDate]);
                    domain.push(["create_date", "<=", endDate]);
                }
            }
    
            const today = new Date().toISOString().split("T")[0];
    
            const [
                totalBrands, totalMakes, totalModels, totalMotorcycles,
                totalQuotations, totalSales, totalInvoices, overdue
            ] = await Promise.all([
                this.orm.searchCount("motorcycle.brand", domain),
                this.orm.searchCount("motorcycle.make", domain),
                this.orm.searchCount("motorcycle.mmodel", domain),
                this.orm.searchCount("motorcycle.motorcycle", domain),
                this.orm.searchCount("sale.order", domain),
                this.orm.searchCount("sale.order", [...domain, ["state", "=", "sale"]]),
                this.orm.searchCount("account.move", [...domain, ["move_type", "=", "out_invoice"]]),
                this.orm.searchCount("account.move", [...domain, ["move_type", "=", "out_invoice"], ["payment_state", "=", "not_paid"], ["invoice_date_due", "<", today]])
            ]);
    
            this.state.totalBrands = totalBrands;
            this.state.totalMakes = totalMakes;
            this.state.totalModels = totalModels;
            this.state.totalMotorcycles = totalMotorcycles;
            this.state.totalQuotations = totalQuotations;
            this.state.totalSales = totalSales;
            this.state.totalInvoices = totalInvoices;
            this.state.overdue = overdue;
            this.state.domain = domain;
    
        } catch (error) {
            console.error("Error fetching motorcycle data:", error);
        }
    }
    

    // async getVehicleCounts() {
    //     try {
    //         let domain = [];

    //         // Priority: Date Range Filter (If both start & end dates are selected, ignore daily/monthly filters)
    //         if (this.state.startDate && this.state.endDate) {
    //             domain.push(["create_date", ">=", this.state.startDate]);
    //             domain.push(["create_date", "<=", this.state.endDate]);
    //         }
    //         // If no date range is selected, use Daily, Weekly, or Monthly filter
    //         else if (this.state.custom) {
    //             const today = new Date();
    //             let startDate, endDate;

    //             if (this.state.custom === "daily") {
    //                 startDate = today.toISOString().split("T")[0]; // Today's date
    //                 endDate = today.toISOString().split("T")[0];

    //             } else if (this.state.custom === "weekly") {
    //                 const firstDayOfWeek = new Date(today);
    //                 firstDayOfWeek.setDate(today.getDate() - today.getDay()); // Start of the week (Sunday)

    //                 startDate = firstDayOfWeek.toISOString().split("T")[0];
    //                 endDate = today.toISOString().split("T")[0];

    //             } else if (this.state.custom === "monthly") {
    //                 const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);

    //                 startDate = firstDayOfMonth.toISOString().split("T")[0];
    //                 endDate = today.toISOString().split("T")[0];
    //             }

    //             domain.push(["create_date", ">=", startDate]);
    //             domain.push(["create_date", "<=", endDate]);
    //         }

    //         // Fetch data with the final domain
    //         const today = new Date().toISOString().split("T")[0];
    //         console.log("\n\n\n\n..today...today..",today);
    //         const [totalBrands, totalMakes, totalModels, totalMotorcycles, totalQuotations, totalSales, totalInvoices, overdue] = await Promise.all([
    //             this.orm.searchCount("motorcycle.brand", domain),
    //             this.orm.searchCount("motorcycle.make", domain),
    //             this.orm.searchCount("motorcycle.mmodel", domain),
    //             this.orm.searchCount("motorcycle.motorcycle", domain),
    //             this.orm.searchCount("sale.order", domain),
    //             this.orm.searchCount("sale.order", [...domain, ["state", "=", "sale"]]),
    //             this.orm.searchCount("account.move", [...domain, ["move_type", "=", "out_invoice"]]),
    //             this.orm.searchCount("account.move", [...domain, ["move_type", "=", "out_invoice"], ["payment_state", "=", "not_paid"] , ["invoice_date_due", "<", today]])
    //         ]);

    //         // Update state
    //         this.state.totalBrands = totalBrands;
    //         this.state.totalMakes = totalMakes;
    //         this.state.totalModels = totalModels;
    //         this.state.totalMotorcycles = totalMotorcycles;
    //         this.state.totalQuotations = totalQuotations;
    //         this.state.totalSales = totalSales;
    //         this.state.totalInvoices = totalInvoices;
    //         this.state.overdue = overdue;

    //         console.log("Updated Data based on filters:", this.state);

    //     } catch (error) {
    //         console.error("Error fetching motorcycle data:", error);
    //     }
    // }


    // onDateFilterChange(event) {
    //     this.state.custom = event.target.value;

    //     // Reset the start & end dates when choosing Daily/Weekly/Monthly
    //     this.state.startDate = null;
    //     this.state.endDate = null;

    //     console.log("Selected Filter:", this.state.custom);
    //     this.getVehicleCounts(); // Fetch data based on selected filter
    // }



    mounted() {
        const filter = this.state.custom;
        const dropdown = document.getElementById('date-filter');
        if (dropdown) {
            dropdown.value = filter; // Update dropdown UI
        }

        // Fetch data for saved/default filter
        this.getVehicleCounts();
    }
    


    onDateFilterChange(event) {
        this.state.custom = event.target.value;
        localStorage.setItem('salesFilter', this.state.custom);
    
        this.state.startDate = null;
        this.state.endDate = null;
    
        this.getVehicleCounts();
    }
    


    // onDateChange(ev) {
    //     const { id, value } = ev.target;

    //     if (id === "start-date") {
    //         this.state.startDate = value;
    //     } else if (id === "end-date") {
    //         this.state.endDate = value;
    //     }
    //     this.state.custom = "";
    //     this.getVehicleCounts();
    // }

   
    onDateChange(ev) {
        const { id, value } = ev.target;
    
        if (id === "start-date") {
            this.state.startDate = value;
            localStorage.setItem("salesStartDate", value);
        } else if (id === "end-date") {
            this.state.endDate = value;
            localStorage.setItem("salesEndDate", value);
        }
    
        localStorage.setItem("salesFilter", "custom");
        this.state.custom = "";
        this.getVehicleCounts();
    }
    


    onChartTypeChange(event) {
        this.state.chartType = event.target.value;
        console.log("Selected Chart Type:", this.state.chartType);
    }

    onChartTypeChangeProducts(event) {
        this.state.productcharttype = event.target.value;
        console.log("Selected Chart Type:", this.state.productcharttype);

    }



    // card click

    // async viewallVehicles() {
    //     const action = await this.orm.call("motorcycle.motorcycle", "viewVehicle", ["", ""], {});
    //     console.log(action)
    //     this.actionService.doAction(action)
    // }


    async viewallVehicles() {
        let domain = this.getCurrentDomain(); // Get current domain filter
        const action = await this.orm.call("motorcycle.motorcycle", "viewVehicle", ["", domain], {});
        console.log(action);
        this.actionService.doAction(action);
    }


    async viewallVehiclesModel() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("motorcycle.mmodel", "viewVehicleModel", ["", domain], {});
        console.log(action)
        this.actionService.doAction(action)
    }

    async viewallVehiclesMake() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("motorcycle.make", "viewVehicleMake", ["", domain], {});
        console.log(action)
        this.actionService.doAction(action)
    }

    async viewallVehiclesBrand() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("motorcycle.brand", "viewVehicleBrand", ["", domain], {});
        console.log(action)
        this.actionService.doAction(action)
    }

    async viewallQuotation() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("sale.order", "viewQuotation", ["", domain], {});
        console.log(action)
        this.actionService.doAction(action)
    }



    async viewallSaleOrder() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("sale.order", "viewSaleOrder", ["", domain], {});
        console.log(action);

        this.actionService.doAction(action);
    }

    async viewallInvoice() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("account.move", "Invoice", ["", domain], {});
        console.log(action);
        this.actionService.doAction(action);
    }


    async Overdue() {
        let domain = this.getCurrentDomain();
        const action = await this.orm.call("account.move", "Overdue", ["", domain], {});
        console.log(action);
        this.actionService.doAction(action);
    }


}






VehicleDashboard.template = "owl.VehicleDashboard"
VehicleDashboard.components = { VehiclesCardall, VehiclesModel, VehiclesMake, VehiclesBrand, VehiclesQuotations, VehiclesSales, Invoices, Overdue, VehicleChartRendorBar, ProductLine, VehicleChartRendorline, VehicleChartRendorpie, VehicleChartRendordoughnut, ProductBar, Productpie, Productdoughnut }
registry.category("actions").add("sh_auto_part_vehicle.custom_dashboard", VehicleDashboard);







