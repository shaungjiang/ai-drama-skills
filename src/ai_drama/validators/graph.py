from __future__ import annotations

PRIMITIVES = {"INT", "FLOAT", "STRING", "BOOLEAN"}


def is_link(value):
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int)


def validate_graph(graph, nodes=None):
    errors = []
    if not isinstance(graph, dict) or not graph:
        return ["API graph must be a non-empty object"]
    edges = {}
    for nid, node in graph.items():
        if not isinstance(nid, str) or not nid.isdigit():
            errors.append(f"Invalid node ID {nid}")
        if not isinstance(node, dict) or not isinstance(node.get("inputs"), dict) or not isinstance(node.get("class_type"), str):
            errors.append(f"Malformed node {nid}")
            continue
        edges[nid] = []
        for name, value in node["inputs"].items():
            if is_link(value):
                parent, port = value
                edges[nid].append(parent)
                if parent not in graph or port < 0:
                    errors.append(f"{nid}.{name}: dangling link {value}")
        if nodes is None:
            continue
        schema = nodes.get(node["class_type"])
        if schema is None:
            errors.append(f"Node unavailable: {node['class_type']}")
            continue
        required = schema.get("input", {}).get("required", {})
        optional = schema.get("input", {}).get("optional", {})
        definitions = required | optional
        for name in required:
            if name not in node["inputs"]:
                errors.append(f"{nid}.{name}: required input missing")
        for name, value in node["inputs"].items():
            if name not in definitions:
                errors.append(f"{nid}.{name}: unknown input")
                continue
            spec = definitions[name]
            dtype = spec[0]
            opts = spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            if is_link(value):
                parent, port = value
                output = nodes.get(graph.get(parent, {}).get("class_type"), {}).get("output", [])
                target = "COMBO" if isinstance(dtype, list) else dtype
                if port >= len(output):
                    errors.append(f"{nid}.{name}: invalid output port")
                elif target != "*" and output[port] not in {target, "*"}:
                    errors.append(f"{nid}.{name}: port type {output[port]} != {target}")
            elif isinstance(dtype, list):
                # Uploaded image choices are dynamic and validated by the server.
                if value not in dtype and not opts.get("image_upload"):
                    errors.append(f"{nid}.{name}: unavailable choice {value}")
            elif dtype in PRIMITIVES:
                good = {"INT": isinstance(value, int) and not isinstance(value, bool), "FLOAT": isinstance(value, (int, float)) and not isinstance(value, bool), "STRING": isinstance(value, str), "BOOLEAN": isinstance(value, bool)}[dtype]
                if not good:
                    errors.append(f"{nid}.{name}: invalid {dtype}")
                elif dtype in {"INT", "FLOAT"}:
                    if value < opts.get("min", float("-inf")) or value > opts.get("max", float("inf")):
                        errors.append(f"{nid}.{name}: out of range")
                    if dtype == "INT" and opts.get("step", 1) > 1 and (value-opts.get("min", 0)) % opts["step"]:
                        errors.append(f"{nid}.{name}: must align to step {opts['step']}")
            else:
                errors.append(f"{nid}.{name}: {dtype} requires connected input")
    visiting, visited = set(), set()

    def visit(nid):
        if nid in visiting:
            errors.append("Cycle detected")
            return
        if nid in visited:
            return
        visiting.add(nid)
        for parent in edges.get(nid, []):
            visit(parent)
        visiting.remove(nid)
        visited.add(nid)

    for nid in edges:
        visit(nid)
    if nodes and not any(nodes.get(n.get("class_type"), {}).get("output_node") for n in graph.values() if isinstance(n, dict)):
        errors.append("No output node")
    return sorted(set(errors))


def api_to_visual(graph, nodes):
    errors = validate_graph(graph, nodes)
    if errors:
        raise ValueError("; ".join(errors))
    visual_nodes, links = [], []
    by_id = {}
    for order, (nid, node) in enumerate(graph.items()):
        schema = nodes[node["class_type"]]
        definitions = schema.get("input", {}).get("required", {}) | schema.get("input", {}).get("optional", {})
        entry = {"id": int(nid), "type": node["class_type"], "pos": [(order % 4) * 380, (order // 4) * 340], "size": [340, 260], "flags": {}, "order": order, "mode": 0, "inputs": [], "outputs": [{"name": name, "type": dtype, "links": []} for name, dtype in zip(schema.get("output_name", schema.get("output", [])), schema.get("output", []))], "properties": {"Node name for S&R": node["class_type"]}, "widgets_values": []}
        # Widget order follows object_info required/optional order, not API dict order.
        for name, spec in definitions.items():
            dtype, opts = spec[0], spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            widget = isinstance(dtype, list) or dtype in PRIMITIVES
            value = node["inputs"].get(name)
            if widget and not is_link(value):
                if name not in node["inputs"]:
                    continue
                entry["widgets_values"].append(value)
                if opts.get("control_after_generate"):
                    entry["widgets_values"].append("fixed")
                if opts.get("image_upload"):
                    entry["widgets_values"].append("image")
            else:
                item = {"name": name, "type": "COMBO" if isinstance(dtype, list) else dtype, "link": None}
                if widget:
                    item["widget"] = {"name": name}
                entry["inputs"].append(item)
        visual_nodes.append(entry)
        by_id[nid] = entry
    for nid, node in graph.items():
        for name, value in node["inputs"].items():
            if not is_link(value):
                continue
            parent, port = value
            entry = by_id[nid]
            slot = next(i for i, p in enumerate(entry["inputs"]) if p["name"] == name)
            lid = len(links) + 1
            links.append([lid, int(parent), port, int(nid), slot, by_id[parent]["outputs"][port]["type"]])
            entry["inputs"][slot]["link"] = lid
            by_id[parent]["outputs"][port]["links"].append(lid)
    return {"version": 0.4, "last_node_id": max(map(int, graph)), "last_link_id": len(links), "nodes": visual_nodes, "links": links, "groups": [], "config": {}, "extra": {}}


def visual_to_api(visual, nodes):
    """Convert flat core-node workflows; reject ambiguous subgraphs/bypassed nodes."""
    if visual.get("definitions", {}).get("subgraphs"):
        raise ValueError("Subgraph workflow needs a frontend API export; import workflow_api.json instead")
    links = {link[0]: link for link in visual.get("links", [])}
    result = {}
    for node in visual["nodes"]:
        kind = node["type"]
        if kind in {"Note", "MarkdownNote"}:
            continue
        if node.get("mode", 0) != 0 or kind not in nodes:
            raise ValueError(f"Unsupported/bypassed node {kind}; use frontend API export")
        definitions = nodes[kind]["input"].get("required", {}) | nodes[kind]["input"].get("optional", {})
        widgets = iter(node.get("widgets_values", []))
        inputs = {}
        input_ports = {i["name"]: i for i in node.get("inputs", [])}
        for name, spec in definitions.items():
            dtype, opts = spec[0], spec[1] if len(spec) > 1 and isinstance(spec[1], dict) else {}
            port = input_ports.get(name, {})
            if port.get("link") is not None:
                link = links[port["link"]]
                inputs[name] = [str(link[1]), link[2]]
            elif isinstance(dtype, list) or dtype in PRIMITIVES:
                try:
                    inputs[name] = next(widgets)
                except StopIteration:
                    if name in nodes[kind]["input"].get("required", {}):
                        raise ValueError(f"Missing widget {kind}.{name}")
                    continue
                if opts.get("control_after_generate"):
                    next(widgets, None)
                if opts.get("image_upload"):
                    next(widgets, None)
        result[str(node["id"])] = {"class_type": kind, "inputs": inputs}
    errors = validate_graph(result, nodes)
    if errors:
        raise ValueError("; ".join(errors))
    return result
