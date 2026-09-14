/** @odoo-module **/
import {
    Component,
    onMounted,
    onWillStart,
    onWillUnmount,
    onWillUpdateProps,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

const TYPES = ["text", "barcode", "qrcode", "box", "line"];
const PX_PER_MM = 96 / 25.4;
const MAX_HISTORY = 60;

export class IckabLabelDesignerField extends Component {
    static template = "ickab_label_studio.LabelDesignerField";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.rootRef = useRef("root");
        this.canvasRef = useRef("canvas");
        this.state = useState({
            design: this.parseDesignValue(this.props.record.data[this.props.name]),
            selected: null,
            fields: [],
            fieldSearch: "",
            fieldsLoading: false,
            fieldsError: "",
            relationPath: "",
            breadcrumbs: [],
            currentModelLabel: "",
            collectionInPath: false,
            loadedModelId: false,
            loadedRelationPath: "",
            loadedDesignValue: this.props.record.data[this.props.name] || "",
            tool: "select",
            operation: null,
            zoom: 150,
            gridVisible: true,
            snapEnabled: true,
            gridMm: 1,
            history: [],
            future: [],
        });

        onWillStart(async () => this.loadFields(this.modelId, ""));

        useEffect(
            () => {
                const modelId = this.modelId;
                if (modelId !== this.state.loadedModelId) this.loadFields(modelId, "");
            },
            () => [this.modelId]
        );

        onWillUpdateProps(async (nextProps) => {
            const nextValue = nextProps.record.data[nextProps.name] || "";
            if (nextValue !== this.state.loadedDesignValue && !this.state.operation) {
                this.state.design = this.parseDesignValue(nextValue, nextProps.record);
                this.state.loadedDesignValue = nextValue;
                this.state.selected = null;
                this.state.history = [];
                this.state.future = [];
            }
            const nextModelId = this.modelIdFromRecord(nextProps.record);
            if (nextModelId !== this.state.loadedModelId) await this.loadFields(nextModelId, "");
        });

        onMounted(() => window.addEventListener("keydown", this.onKeyDown));
        onWillUnmount(() => {
            window.removeEventListener("keydown", this.onKeyDown);
            this.detachOperationListeners();
        });
    }

    get readonly() {
        return Boolean(this.props.readonly);
    }

    widthFromRecord(record = this.props.record) {
        return Math.max(1, Number(record?.data?.width_mm || 50));
    }

    heightFromRecord(record = this.props.record) {
        return Math.max(1, Number(record?.data?.height_mm || 30));
    }

    get widthMm() {
        return this.widthFromRecord();
    }

    get heightMm() {
        return this.heightFromRecord();
    }

    get safeMarginMm() {
        return Math.max(0, Number(this.props.record?.data?.safe_margin_mm || 0));
    }

    get shape() {
        return this.props.record?.data?.shape || "rectangle";
    }

    parseDesignValue(value, record = this.props.record) {
        try {
            const parsed = JSON.parse(value || "{}");
            if (!Array.isArray(parsed.elements)) parsed.elements = [];
            const version = Number(parsed.version || 1);
            if (version === 1) {
                const width = this.widthFromRecord(record);
                const height = this.heightFromRecord(record);
                parsed.elements = parsed.elements.map((el, index) => ({
                    ...el,
                    x_mm: Number(el.x || 0) * width / 100,
                    y_mm: Number(el.y || 0) * height / 100,
                    w_mm: Math.max(0.1, Number(el.w || 20) * width / 100),
                    h_mm: Math.max(0.1, Number(el.h || 10) * height / 100),
                    z: Number(el.z ?? index + 1),
                    thickness_mm: Number(el.thickness_mm || 0.25),
                    line_direction: el.line_direction || "horizontal",
                })).map((el) => {
                    delete el.x; delete el.y; delete el.w; delete el.h; delete el.thickness;
                    return el;
                });
                parsed.version = 2;
            }
            if (Number(parsed.version) !== 2) return { version: 2, elements: [] };
            parsed.elements = parsed.elements.map((el, index) => ({
                ...el,
                z: Number(el.z ?? index + 1),
                x_mm: Number(el.x_mm || 0),
                y_mm: Number(el.y_mm || 0),
                w_mm: Math.max(0.1, Number(el.w_mm || 1)),
                h_mm: Math.max(0.1, Number(el.h_mm || 1)),
            }));
            return parsed;
        } catch {
            return { version: 2, elements: [] };
        }
    }

    modelIdFromRecord(record) {
        const value = record?.data?.model_id;
        if (!value) return false;
        if (Array.isArray(value)) return Number(value[0]) || false;
        if (typeof value === "object") return Number(value.id || value.resId || value.res_id || value[0]) || false;
        return Number(value) || false;
    }

    get modelId() {
        return this.modelIdFromRecord(this.props.record);
    }

    get modelDisplayName() {
        const value = this.props.record?.data?.model_id;
        if (!value) return "";
        if (Array.isArray(value)) return value[1] || "";
        if (typeof value === "object") return value.display_name || value.name || "";
        return "";
    }

    async loadFields(modelId = this.modelId, relationPath = this.state.relationPath || "") {
        modelId = Number(modelId) || false;
        relationPath = modelId ? String(relationPath || "") : "";
        const requestKey = `${modelId || 0}:${relationPath}`;
        this.state.loadedModelId = modelId;
        this.state.loadedRelationPath = relationPath;
        this.state.fieldsError = "";
        if (!modelId) {
            this.state.fields = [];
            this.state.relationPath = "";
            this.state.breadcrumbs = [];
            this.state.currentModelLabel = "";
            this.state.collectionInPath = false;
            this.state.fieldsLoading = false;
            return;
        }
        this.state.fieldsLoading = true;
        try {
            const catalog = await this.orm.call(
                "ickab.label.template",
                "get_field_catalog",
                [modelId, relationPath]
            );
            const activeKey = `${this.modelId || 0}:${this.state.loadedRelationPath || ""}`;
            if (activeKey !== requestKey) return;
            this.state.fields = Array.isArray(catalog?.fields) ? catalog.fields : [];
            this.state.relationPath = catalog?.relation_path || "";
            this.state.breadcrumbs = Array.isArray(catalog?.breadcrumbs) ? catalog.breadcrumbs : [];
            this.state.currentModelLabel = catalog?.current_model_label || this.modelDisplayName || "";
            this.state.collectionInPath = Boolean(catalog?.collection_in_path);
            this.state.fieldSearch = "";
        } catch {
            const activeKey = `${this.modelId || 0}:${this.state.loadedRelationPath || ""}`;
            if (activeKey !== requestKey) return;
            this.state.fields = [];
            this.state.fieldsError = "No fue posible cargar los campos de esta relación.";
            this.notification.add(this.state.fieldsError, { type: "danger" });
        } finally {
            const activeKey = `${this.modelId || 0}:${this.state.loadedRelationPath || ""}`;
            if (activeKey === requestKey) this.state.fieldsLoading = false;
        }
    }

    enterRelation(field) {
        if (!field?.navigable || !field?.path) return;
        this.loadFields(this.modelId, field.path);
    }

    goBreadcrumb(crumb) {
        this.loadFields(this.modelId, crumb?.path || "");
    }

    get canBindSelected() {
        return Boolean(this.selected && ["text", "barcode", "qrcode"].includes(this.selected.type));
    }

    bindFieldToSelected(field) {
        const el = this.selected;
        if (this.readonly || !el || !["text", "barcode", "qrcode"].includes(el.type) || !field?.path) return;
        this.checkpoint();
        el.source = "field";
        el.value = "";
        el.sample = field.label || field.name || field.path;
        el.field_path = field.path;
        el.field_label = field.label || field.name || field.path;
        el.field_type = field.type || "";
        el.field_is_collection = Boolean(field.is_collection);
        el.aggregate = field.is_collection ? (el.aggregate || "first") : "";
        el.separator = field.is_collection ? (el.separator ?? ", ") : "";
        this.persist();
    }

    get filteredFields() {
        const search = (this.state.fieldSearch || "").trim().toLocaleLowerCase();
        if (!search) return this.state.fields;
        return this.state.fields.filter((field) => {
            const haystack = `${field.label || ""} ${field.name || ""} ${field.type || ""}`.toLocaleLowerCase();
            return haystack.includes(search);
        });
    }

    get sortedElements() {
        return [...this.state.design.elements].sort((a, b) => Number(a.z || 0) - Number(b.z || 0));
    }

    get selected() {
        return this.state.design.elements.find((el) => el.id === this.state.selected) || null;
    }

    get canUndo() {
        return this.state.history.length > 0 && !this.readonly;
    }

    get canRedo() {
        return this.state.future.length > 0 && !this.readonly;
    }

    setFieldSearch(ev) {
        this.state.fieldSearch = ev.target.value || "";
    }

    snapshot() {
        return JSON.stringify(this.state.design);
    }

    checkpoint() {
        if (this.readonly) return;
        const current = this.snapshot();
        if (this.state.history[this.state.history.length - 1] !== current) {
            this.state.history.push(current);
            if (this.state.history.length > MAX_HISTORY) this.state.history.shift();
        }
        this.state.future = [];
    }

    async persist() {
        const value = JSON.stringify(this.state.design);
        this.state.loadedDesignValue = value;
        await this.props.record.update({ [this.props.name]: value });
    }

    undo() {
        if (!this.canUndo) return;
        this.state.future.push(this.snapshot());
        const previous = this.state.history.pop();
        this.state.design = this.parseDesignValue(previous);
        this.state.selected = null;
        this.persist();
    }

    redo() {
        if (!this.canRedo) return;
        this.state.history.push(this.snapshot());
        const next = this.state.future.pop();
        this.state.design = this.parseDesignValue(next);
        this.state.selected = null;
        this.persist();
    }

    newElementId(prefix = "el") {
        return `${prefix}_${Date.now()}_${Math.floor(Math.random() * 100000)}`;
    }

    maxZ() {
        return Math.max(0, ...this.state.design.elements.map((el) => Number(el.z || 0)));
    }

    snap(value) {
        value = Number(value || 0);
        if (!this.state.snapEnabled) return value;
        const grid = Math.max(0.1, Number(this.state.gridMm || 1));
        return Math.round(value / grid) * grid;
    }

    clamp(value, min, max) {
        return Math.min(Math.max(Number(value || 0), min), Math.max(min, max));
    }

    clampElement(el) {
        el.w_mm = this.clamp(el.w_mm, 0.1, this.widthMm);
        el.h_mm = this.clamp(el.h_mm, 0.1, this.heightMm);
        el.x_mm = this.clamp(el.x_mm, 0, this.widthMm - el.w_mm);
        el.y_mm = this.clamp(el.y_mm, 0, this.heightMm - el.h_mm);
        if (el.type === "qrcode") {
            const size = Math.min(el.w_mm, el.h_mm, this.widthMm - el.x_mm, this.heightMm - el.y_mm);
            el.w_mm = el.h_mm = Math.max(1, size);
        }
    }

    nextPosition() {
        const index = this.state.design.elements.length;
        const offset = (index % 8) * Math.max(1, Number(this.state.gridMm || 1));
        return {
            x_mm: this.clamp(this.safeMarginMm + offset, 0, Math.max(0, this.widthMm - 10)),
            y_mm: this.clamp(this.safeMarginMm + offset, 0, Math.max(0, this.heightMm - 5)),
        };
    }

    makeElement(type, xMm, yMm) {
        const id = this.newElementId(type === "text" ? "text" : type);
        const base = {
            id,
            type,
            x_mm: this.snap(xMm),
            y_mm: this.snap(yMm),
            w_mm: 30,
            h_mm: 7,
            z: this.maxZ() + 1,
            source: "static",
            value: "Texto",
            sample: "",
            field_path: "",
            field_label: "",
            field_type: "",
            field_is_collection: false,
            aggregate: "",
            separator: ", ",
            font_mm: 3,
            align: "L",
            max_lines: 1,
            barcode_type: "code128",
            human_readable: true,
            magnification: 4,
            thickness_mm: 0.25,
            line_direction: "horizontal",
            rounding: 0,
        };
        if (type === "barcode") {
            base.value = "1234567890";
            base.w_mm = 40;
            base.h_mm = 14;
        } else if (type === "qrcode") {
            base.value = "https://ickab.mx";
            base.w_mm = base.h_mm = 18;
        } else if (type === "box") {
            base.value = "";
            base.w_mm = 30;
            base.h_mm = 15;
        } else if (type === "line") {
            base.value = "";
            base.w_mm = 30;
            base.h_mm = 0.5;
        }
        this.clampElement(base);
        return base;
    }

    add(type) {
        if (this.readonly || !TYPES.includes(type)) return;
        this.checkpoint();
        const position = this.nextPosition();
        const element = this.makeElement(type, position.x_mm, position.y_mm);
        this.state.design.elements.push(element);
        this.state.selected = element.id;
        this.state.tool = "select";
        this.persist();
    }

    addField(field) {
        const position = this.nextPosition();
        this.addFieldAt(field, position.x_mm, position.y_mm);
    }

    addFieldAt(field, xMm, yMm) {
        if (this.readonly || !field?.path) return;
        this.checkpoint();
        const element = this.makeElement("text", xMm, yMm);
        element.id = this.newElementId("field");
        element.source = "field";
        element.value = "";
        element.sample = field.label || field.name || field.path;
        element.field_path = field.path;
        element.field_label = field.label || field.name || field.path;
        element.field_type = field.type || "";
        element.field_is_collection = Boolean(field.is_collection);
        element.aggregate = field.is_collection ? "first" : "";
        element.separator = field.is_collection ? ", " : "";
        element.w_mm = Math.min(45, Math.max(15, this.widthMm - element.x_mm));
        element.h_mm = Math.min(7, Math.max(2, this.heightMm - element.y_mm));
        this.clampElement(element);
        this.state.design.elements.push(element);
        this.state.selected = element.id;
        this.state.tool = "select";
        this.persist();
    }

    onFieldDragStart(ev, field) {
        if (this.readonly || !field?.path) {
            ev.preventDefault();
            return;
        }
        const payload = JSON.stringify({
            name: field.name, path: field.path, label: field.label, type: field.type,
            relation: field.relation || "", is_collection: Boolean(field.is_collection),
        });
        ev.dataTransfer.setData("application/x-ickab-label-field", payload);
        ev.dataTransfer.setData("text/plain", payload);
        ev.dataTransfer.effectAllowed = "copy";
    }

    onCanvasDragOver(ev) {
        if (this.readonly) return;
        ev.preventDefault();
        ev.dataTransfer.dropEffect = "copy";
    }

    onCanvasDrop(ev) {
        if (this.readonly) return;
        ev.preventDefault();
        let raw = ev.dataTransfer.getData("application/x-ickab-label-field") || ev.dataTransfer.getData("text/plain");
        if (!raw) return;
        try {
            const field = JSON.parse(raw);
            const point = this.pointFromEvent(ev);
            this.addFieldAt(field, point.x_mm, point.y_mm);
        } catch {
            this.notification.add("No fue posible agregar el campo al lienzo.", { type: "warning" });
        }
    }

    select(id) {
        this.state.selected = id;
        this.state.tool = "select";
    }

    removeSelected() {
        if (this.readonly || !this.state.selected) return;
        this.checkpoint();
        this.state.design.elements = this.state.design.elements.filter((el) => el.id !== this.state.selected);
        this.state.selected = null;
        this.persist();
    }

    duplicateSelected() {
        if (this.readonly || !this.selected) return;
        this.checkpoint();
        const clone = JSON.parse(JSON.stringify(this.selected));
        clone.id = this.newElementId("copy");
        clone.x_mm = this.snap(clone.x_mm + Math.max(0.5, this.state.gridMm));
        clone.y_mm = this.snap(clone.y_mm + Math.max(0.5, this.state.gridMm));
        clone.z = this.maxZ() + 1;
        this.clampElement(clone);
        this.state.design.elements.push(clone);
        this.state.selected = clone.id;
        this.persist();
    }

    updateSelected(key, ev) {
        const el = this.selected;
        if (this.readonly || !el) return;
        this.checkpoint();
        let value = ev.target.type === "checkbox" ? ev.target.checked : ev.target.value;
        const numeric = [
            "x_mm", "y_mm", "w_mm", "h_mm", "font_mm", "max_lines",
            "magnification", "thickness_mm", "rounding", "z",
        ];
        if (numeric.includes(key)) value = Number(value || 0);
        el[key] = value;
        if (key === "type") {
            if (value === "barcode") {
                el.barcode_type ||= "code128";
                el.human_readable ??= true;
            } else if (value === "qrcode") {
                el.magnification ||= 4;
                const size = Math.min(Math.max(el.w_mm, el.h_mm, 12), this.widthMm - el.x_mm, this.heightMm - el.y_mm);
                el.w_mm = el.h_mm = size;
            }
        }
        this.clampElement(el);
        this.persist();
    }

    setTool(tool) {
        if (this.readonly || !["select", ...TYPES].includes(tool)) return;
        this.state.tool = tool;
    }

    pointFromClient(clientX, clientY, rect = null) {
        const canvas = this.canvasRef.el;
        rect = rect || canvas?.getBoundingClientRect();
        if (!rect) return { x_mm: 0, y_mm: 0 };
        return {
            x_mm: this.snap(this.clamp(((clientX - rect.left) / rect.width) * this.widthMm, 0, this.widthMm)),
            y_mm: this.snap(this.clamp(((clientY - rect.top) / rect.height) * this.heightMm, 0, this.heightMm)),
        };
    }

    pointFromEvent(ev) {
        return this.pointFromClient(ev.clientX, ev.clientY);
    }

    startCanvasDraw(ev) {
        if (this.readonly) return;
        this.focusDesigner(ev);
        if (this.state.tool === "select") {
            if (ev.target === ev.currentTarget) this.state.selected = null;
            return;
        }
        if (ev.button !== 0) return;
        const type = this.state.tool;
        const rect = ev.currentTarget.getBoundingClientRect();
        const start = this.pointFromClient(ev.clientX, ev.clientY, rect);
        this.checkpoint();
        const element = this.makeElement(type, start.x_mm, start.y_mm);
        element.w_mm = type === "line" ? 0.5 : 0.5;
        element.h_mm = 0.5;
        this.state.design.elements.push(element);
        this.state.selected = element.id;
        this.state.operation = { kind: "draw", id: element.id, start, rect, type };
        this.attachOperationListeners();
        ev.preventDefault();
    }

    startDrag(ev, id) {
        if (this.readonly || ev.button !== 0) return;
        const el = this.state.design.elements.find((item) => item.id === id);
        if (!el) return;
        this.focusDesigner(ev);
        this.checkpoint();
        this.state.selected = id;
        const rect = this.canvasRef.el?.getBoundingClientRect();
        this.state.operation = {
            kind: "drag",
            id,
            startClientX: ev.clientX,
            startClientY: ev.clientY,
            x_mm: Number(el.x_mm || 0),
            y_mm: Number(el.y_mm || 0),
            rect,
        };
        this.attachOperationListeners();
        ev.preventDefault();
        ev.stopPropagation();
    }

    startResize(ev, id, handle) {
        if (this.readonly || ev.button !== 0) return;
        const el = this.state.design.elements.find((item) => item.id === id);
        if (!el) return;
        this.focusDesigner(ev);
        this.checkpoint();
        this.state.selected = id;
        this.state.operation = {
            kind: "resize",
            id,
            handle,
            startClientX: ev.clientX,
            startClientY: ev.clientY,
            rect: this.canvasRef.el?.getBoundingClientRect(),
            x_mm: Number(el.x_mm || 0),
            y_mm: Number(el.y_mm || 0),
            w_mm: Number(el.w_mm || 1),
            h_mm: Number(el.h_mm || 1),
        };
        this.attachOperationListeners();
        ev.preventDefault();
        ev.stopPropagation();
    }

    attachOperationListeners() {
        window.addEventListener("mousemove", this.onOperationMove);
        window.addEventListener("mouseup", this.stopOperation, { once: true });
    }

    detachOperationListeners() {
        window.removeEventListener("mousemove", this.onOperationMove);
        window.removeEventListener("mouseup", this.stopOperation);
    }

    onOperationMove = (ev) => {
        const op = this.state.operation;
        if (!op) return;
        const el = this.state.design.elements.find((item) => item.id === op.id);
        if (!el || !op.rect) return;

        if (op.kind === "draw") {
            const point = this.pointFromClient(ev.clientX, ev.clientY, op.rect);
            let x = Math.min(op.start.x_mm, point.x_mm);
            let y = Math.min(op.start.y_mm, point.y_mm);
            let w = Math.abs(point.x_mm - op.start.x_mm);
            let h = Math.abs(point.y_mm - op.start.y_mm);
            if (op.type === "line") {
                const horizontal = w >= h;
                el.line_direction = horizontal ? "horizontal" : "vertical";
                if (horizontal) h = Math.max(0.3, el.thickness_mm || 0.25);
                else w = Math.max(0.3, el.thickness_mm || 0.25);
            }
            el.x_mm = x; el.y_mm = y; el.w_mm = Math.max(0.1, w); el.h_mm = Math.max(0.1, h);
            if (op.type === "qrcode") {
                const size = Math.max(w, h, 0.5);
                el.w_mm = el.h_mm = size;
            }
            this.clampElement(el);
            return;
        }

        const dx = ((ev.clientX - op.startClientX) / op.rect.width) * this.widthMm;
        const dy = ((ev.clientY - op.startClientY) / op.rect.height) * this.heightMm;
        if (op.kind === "drag") {
            el.x_mm = this.snap(op.x_mm + dx);
            el.y_mm = this.snap(op.y_mm + dy);
            this.clampElement(el);
            return;
        }

        if (op.kind === "resize") {
            let x = op.x_mm, y = op.y_mm, w = op.w_mm, h = op.h_mm;
            if (op.handle.includes("e")) w = op.w_mm + dx;
            if (op.handle.includes("s")) h = op.h_mm + dy;
            if (op.handle.includes("w")) { x = op.x_mm + dx; w = op.w_mm - dx; }
            if (op.handle.includes("n")) { y = op.y_mm + dy; h = op.h_mm - dy; }
            x = this.snap(x); y = this.snap(y); w = this.snap(Math.max(0.5, w)); h = this.snap(Math.max(0.5, h));
            if (el.type === "qrcode") {
                const size = Math.max(1, Math.max(w, h));
                w = h = size;
            }
            el.x_mm = x; el.y_mm = y; el.w_mm = w; el.h_mm = h;
            this.clampElement(el);
        }
    };

    stopOperation = () => {
        const op = this.state.operation;
        this.detachOperationListeners();
        this.state.operation = null;
        if (!op) return;
        const el = this.state.design.elements.find((item) => item.id === op.id);
        if (el && op.kind === "draw") {
            const tooSmall = el.w_mm < 1 || el.h_mm < 1;
            if (tooSmall && op.type !== "line") {
                const fallback = this.makeElement(op.type, el.x_mm, el.y_mm);
                Object.assign(el, { w_mm: fallback.w_mm, h_mm: fallback.h_mm });
                this.clampElement(el);
            }
            if (op.type === "line") {
                if (el.line_direction === "vertical") el.w_mm = Math.max(0.3, el.thickness_mm || 0.25);
                else el.h_mm = Math.max(0.3, el.thickness_mm || 0.25);
                this.clampElement(el);
            }
            this.state.tool = "select";
        }
        this.persist();
    };

    nudge(dx, dy) {
        const el = this.selected;
        if (this.readonly || !el) return;
        this.checkpoint();
        el.x_mm = this.snap(el.x_mm + dx);
        el.y_mm = this.snap(el.y_mm + dy);
        this.clampElement(el);
        this.persist();
    }

    alignSelected(where) {
        const el = this.selected;
        if (this.readonly || !el) return;
        this.checkpoint();
        const margin = Math.min(this.safeMarginMm, this.widthMm / 2, this.heightMm / 2);
        const left = margin;
        const top = margin;
        const right = this.widthMm - margin;
        const bottom = this.heightMm - margin;
        if (where === "left") el.x_mm = left;
        if (where === "right") el.x_mm = right - el.w_mm;
        if (where === "hcenter") el.x_mm = (this.widthMm - el.w_mm) / 2;
        if (where === "top") el.y_mm = top;
        if (where === "bottom") el.y_mm = bottom - el.h_mm;
        if (where === "vcenter") el.y_mm = (this.heightMm - el.h_mm) / 2;
        this.clampElement(el);
        this.persist();
    }

    moveLayer(where) {
        const el = this.selected;
        if (this.readonly || !el) return;
        this.checkpoint();
        const values = this.state.design.elements.map((item) => Number(item.z || 0));
        if (where === "front") el.z = Math.max(0, ...values) + 1;
        else el.z = Math.min(0, ...values) - 1;
        this.persist();
    }

    setZoom(value) {
        this.state.zoom = this.clamp(Number(value || 100), 40, 400);
    }

    zoomIn() { this.setZoom(this.state.zoom + 25); }
    zoomOut() { this.setZoom(this.state.zoom - 25); }
    zoomReset() { this.setZoom(100); }
    toggleGrid() { this.state.gridVisible = !this.state.gridVisible; }
    toggleSnap() { this.state.snapEnabled = !this.state.snapEnabled; }
    updateGrid(ev) { this.state.gridMm = this.clamp(Number(ev.target.value || 1), 0.1, 50); }

    elementStyle(el) {
        const left = (Number(el.x_mm || 0) / this.widthMm) * 100;
        const top = (Number(el.y_mm || 0) / this.heightMm) * 100;
        const width = (Number(el.w_mm || 1) / this.widthMm) * 100;
        const height = (Number(el.h_mm || 1) / this.heightMm) * 100;
        return `left:${left}%;top:${top}%;width:${width}%;height:${height}%;z-index:${Number(el.z || 0)};`;
    }

    textStyle(el) {
        const px = Math.max(5, Number(el.font_mm || 3) * PX_PER_MM * (this.state.zoom / 100));
        const align = { C: "center", R: "right", J: "justify", L: "left" }[el.align] || "left";
        return `font-size:${px}px;text-align:${align};line-height:1.05;`;
    }

    canvasStyle() {
        const widthPx = this.widthMm * PX_PER_MM * (this.state.zoom / 100);
        const heightPx = this.heightMm * PX_PER_MM * (this.state.zoom / 100);
        const gx = (Math.max(0.1, this.state.gridMm) / this.widthMm) * 100;
        const gy = (Math.max(0.1, this.state.gridMm) / this.heightMm) * 100;
        const radius = ["circle", "oval"].includes(this.shape) ? "50%" : "0";
        const grid = this.state.gridVisible
            ? `background-size:${gx}% ${gy}%;`
            : "background-image:none;";
        return `width:${widthPx}px;height:${heightPx}px;border-radius:${radius};${grid}`;
    }

    safeZoneStyle() {
        const mx = Math.min(49, (this.safeMarginMm / this.widthMm) * 100);
        const my = Math.min(49, (this.safeMarginMm / this.heightMm) * 100);
        const radius = ["circle", "oval"].includes(this.shape) ? "50%" : "0";
        return `left:${mx}%;right:${mx}%;top:${my}%;bottom:${my}%;border-radius:${radius};`;
    }

    displayValue(el) {
        if (el.source === "field") return el.sample || `[${el.field_label || el.field_path || "campo"}]`;
        return el.value || "";
    }

    previewSrc(el) {
        if (!el || !["barcode", "qrcode"].includes(el.type)) return "";
        const value = this.displayValue(el);
        if (!value) return "";
        if (el.type === "barcode") {
            const kind = el.barcode_type || "code128";
            if (kind === "ean13" && !/^\d{12,13}$/.test(value)) return "";
            if (kind === "upca" && !/^\d{11,12}$/.test(value)) return "";
            if (kind === "code39" && !/^[0-9A-Z .\-$/+%]+$/i.test(value)) return "";
        }
        const types = { code128: "Code128", code39: "Standard39", ean13: "EAN13", upca: "UPCA" };
        const barcodeType = el.type === "qrcode" ? "QR" : (types[el.barcode_type] || "Code128");
        const params = new URLSearchParams({
            barcode_type: barcodeType,
            value,
            width: "600",
            height: "300",
        });
        if (el.type === "barcode" && el.human_readable) params.set("humanreadable", "1");
        return `/report/barcode/?${params.toString()}`;
    }

    lineStyle(el) {
        const thicknessPx = Math.max(1, Number(el.thickness_mm || 0.25) * PX_PER_MM * (this.state.zoom / 100));
        if (el.line_direction === "vertical") return `position:absolute;top:0;bottom:0;left:50%;border-left:${thicknessPx}px solid #111;transform:translateX(-50%);`;
        return `position:absolute;left:0;right:0;top:50%;border-top:${thicknessPx}px solid #111;transform:translateY(-50%);`;
    }

    boxStyle(el) {
        const thicknessPx = Math.max(1, Number(el.thickness_mm || 0.25) * PX_PER_MM * (this.state.zoom / 100));
        const radius = Math.max(0, Math.min(8, Number(el.rounding || 0))) * 2;
        return `width:100%;height:100%;box-sizing:border-box;border:${thicknessPx}px solid #111;border-radius:${radius}px;`;
    }

    formatMm(value) {
        return Number(value || 0).toFixed(2);
    }

    focusDesigner(ev) {
        const target = ev?.target;
        if (target?.closest?.("input,select,textarea,button,a,[contenteditable='true']")) return;
        this.rootRef.el?.focus?.({ preventScroll: true });
    }

    onKeyDown = (ev) => {
        const root = this.rootRef.el;
        if (!root || !root.contains(document.activeElement) || this.readonly) return;
        const target = ev.target;
        if (target?.closest?.("input,select,textarea,[contenteditable='true']")) return;
        const ctrl = ev.ctrlKey || ev.metaKey;
        if (ctrl && ev.key.toLowerCase() === "z") {
            ev.preventDefault();
            if (ev.shiftKey) this.redo(); else this.undo();
            return;
        }
        if (ctrl && ev.key.toLowerCase() === "y") { ev.preventDefault(); this.redo(); return; }
        if (ctrl && ev.key.toLowerCase() === "d") { ev.preventDefault(); this.duplicateSelected(); return; }
        if (["Delete", "Backspace"].includes(ev.key)) { ev.preventDefault(); this.removeSelected(); return; }
        const step = Math.max(0.1, Number(this.state.gridMm || 1)) * (ev.shiftKey ? 10 : 1);
        if (ev.key === "ArrowLeft") { ev.preventDefault(); this.nudge(-step, 0); }
        if (ev.key === "ArrowRight") { ev.preventDefault(); this.nudge(step, 0); }
        if (ev.key === "ArrowUp") { ev.preventDefault(); this.nudge(0, -step); }
        if (ev.key === "ArrowDown") { ev.preventDefault(); this.nudge(0, step); }
    };
}

registry.category("fields").add("ickab_label_designer", {
    component: IckabLabelDesignerField,
    supportedTypes: ["text"],
});
