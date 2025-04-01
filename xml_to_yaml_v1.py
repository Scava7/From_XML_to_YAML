import xml.etree.ElementTree as ET
import tkinter as tk
from tkinter import filedialog, messagebox
import yaml
import os
import re

def scegli_file():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(
        title="Scegli un database SQLite",
        filetypes=[("XML", "*.xml") , ("Tutti i file", "*.*")]
    )

file_path = scegli_file()

# Carica XML
tree = ET.parse(file_path)
base_dir = os.path.dirname(file_path)
root = tree.getroot()
ns = {'ns': 'http://www.3s-software.com/schemas/Symbolconfiguration.xsd'}

# Mappa tipo -> definizione
type_definitions = {}
for typedef in root.findall('.//ns:TypeUserDef', ns):
    typename = typedef.get("name")
    elements = []
    for el in typedef.findall('ns:UserDefElement', ns):
        elements.append({
            'name': el.get("iecname"),
            'type': el.get("type")
        })
    type_definitions[typename] = elements

# Ricorsivamente costruisce la struttura del tipo
def build_structure(type_name, visited=None):
    if visited is None:
        visited = set()
    if type_name in visited:
        return f"<recursive: {clean_type_name(type_name)}>"
    visited.add(type_name)

    if type_name not in type_definitions:
        return clean_type_name(type_name)  # tipo semplice

    result = {}
    for field in type_definitions[type_name]:
        field_name = field["name"]
        field_type = field["type"]
        result[field_name] = build_structure(field_type, visited.copy())
    return result


def clean_type_name(type_name):
    if type_name.startswith("T_ARRAY__"):
        # Rimuove "T_ARRAY__" e sostituisce i doppi underscore con sintassi leggibile
        match = re.match(r"T_ARRAY__(\d+)__(\d+)__OF_(.+)", type_name)
        if match:
            start, end, base_type = match.groups()
            return f"ARRAY [{start}..{end}] OF {base_type}"
    if type_name.startswith("T_"):
        return type_name[2:]  # Rimuove "T_"
    return type_name  # Tipo semplice già pulito


# Funzione ricorsiva per esplorare i Node e Symbol
def parse_nodes(xml_node):
    result = {}

    # Prima gestiamo i Node che hanno attributo 'type' (sono istanze di struttura!)
    for node in xml_node.findall('ns:Node', ns):
        node_name = node.get("name")
        node_type = node.get("type")
        if node_type:  # è un'istanza, come un simbolo
            result[node_name] = build_structure(node_type)
        else:
            result[node_name] = parse_nodes(node)

    # Poi gestiamo i simboli classici
    for symbol in xml_node.findall('ns:Symbol', ns):
        var_name = symbol.get("name")
        var_type = symbol.get("type")
        result[var_name] = build_structure(var_type)

    return result

# Trova il primo nodo che contiene un figlio chiamato IO
program_root = None
for node in root.findall(".//ns:Node", ns):
    for child in node.findall("ns:Node", ns):
        if child.get("name") == "IO":
            program_root = child
            break
    if program_root:
        break

if program_root is None:
    raise ValueError("ERR Nessun nodo 'IO' trovato nel file XML.")

output_tree = parse_nodes(program_root)
output_tree = {"IO": parse_nodes(program_root)}

# Esporta YAML
output_filename = "IO_Struct.yaml"
output_path = os.path.join(base_dir, output_filename)
with open(output_path, "w") as f:
    yaml.dump(output_tree, f, sort_keys=False, allow_unicode=True)

print(f"[OK] File '{output_path}' creato con struttura App_User completa!")
messagebox.showinfo("Successo", f"File generato:\n{output_path}")
