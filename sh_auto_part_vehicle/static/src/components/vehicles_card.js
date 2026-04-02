import { Component } from "@odoo/owl";
import { user } from "@web/core/user";

export class VehiclesCardall extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesCardall.template = "owl.VehiclesCardall"


export class VehiclesModel extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesModel.template = "owl.VehiclesModel"


export class VehiclesMake extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesMake.template = "owl.VehiclesMake"

export class VehiclesBrand extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesBrand.template = "owl.VehiclesBrand"

export class VehiclesQuotations extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesQuotations.template = "owl.VehiclesQuotations"


export class VehiclesSales extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

VehiclesSales.template = "owl.VehiclesSales"

export class Invoices extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

Invoices.template = "owl.Invoices"


export class Overdue extends Component {
    setup() {
        this.user = user;
    }
    get translatedName() {
        const lang = this.user.lang || '';
        if (lang.includes('es-MX')) {
            const translations = {
                'All Vehicles': 'Todos los vehículos',
                'Vehicles Model': 'Modelos de vehículos',
                'Vehicles Make': 'Marcas de vehículos',
                'Vehicles Brand': 'Fabricantes de vehículos',
                'Vehicles Quotations': 'Presupuestos de vehículos',
                'Vehicles Sale Order': 'Pedidos de venta de vehículos',
                'Invoice': 'Facturas',
                'Over due': 'Facturas vencidas'
            };
            return translations[this.props.name] || this.props.name;
        }
        return this.props.name;
    }
}

Overdue.template = "owl.Overdue"
