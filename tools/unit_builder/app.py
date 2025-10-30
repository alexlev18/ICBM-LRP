"""Graphical unit creation tool for the ICBM: Escalation project.

This module provides a small Tkinter application that exposes the most
common unit attributes and exports the data using the text template found in
``unit_template.txt``.  The goal is to help designers quickly draft new units
without having to remember the file syntax by hand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Directory that contains this module.  It is used to load the template file.
BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_PATH = BASE_DIR / "unit_template.txt"


@dataclass
class UnitField:
    """Represents a single form field within the UI."""

    label: str
    var: tk.StringVar
    placeholder: str = ""


class SafeDict(dict):
    """Dict that returns the placeholder if the key is missing.

    ``str.format`` would normally raise a ``KeyError`` when a placeholder is not
    provided.  Returning the placeholder itself makes it easier to spot missing
    values in the generated output without crashing the application.
    """

    def __missing__(self, key: str) -> str:  # pragma: no cover - trivial
        return f"{{{key}}}"


class UnitBuilderApp:
    """Main Tkinter application used to collect unit data."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ICBM: Escalation Unit Creator")
        self.root.geometry("1000x720")
        self.root.minsize(960, 680)

        self.fields: Dict[str, UnitField] = {}
        self.custom_stats: List[Tuple[str, str]] = []

        self._build_layout()
        self._load_default_values()
        self._update_preview()

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------
    def _build_layout(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        form_frame = ttk.Frame(main)
        form_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 12))

        preview_frame = ttk.LabelFrame(main, text="Preview", padding=8)
        preview_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self._build_general_section(form_frame)
        self._build_stats_section(form_frame)
        self._build_description_section(form_frame)
        self._build_custom_stats_section(form_frame)
        self._build_actions(form_frame)

        self.preview_text = tk.Text(
            preview_frame,
            wrap=tk.WORD,
            height=25,
            state=tk.DISABLED,
            font=("Courier New", 10),
        )
        self.preview_text.pack(fill=tk.BOTH, expand=True)

    def _build_general_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="General", padding=8)
        section.pack(fill=tk.X, expand=False, pady=(0, 8))

        self._add_field(section, "name", "Unit Name", row=0, column=0)
        self._add_field(section, "unit_type", "Unit Type", row=0, column=1)
        self._add_field(section, "category", "Category", row=1, column=0)
        self._add_field(section, "faction", "Faction", row=1, column=1)

    def _build_stats_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Combat Stats", padding=8)
        section.pack(fill=tk.X, expand=False, pady=(0, 8))

        labels = [
            ("hit_points", "Hit Points"),
            ("armor", "Armor"),
            ("damage", "Damage"),
            ("range", "Range"),
            ("speed", "Speed"),
            ("detection_range", "Detection Range"),
            ("build_time", "Build Time"),
            ("cost", "Cost"),
        ]

        for index, (field_key, label) in enumerate(labels):
            row, column = divmod(index, 4)
            self._add_field(section, field_key, label, row=row, column=column)

    def _build_description_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Narrative", padding=8)
        section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        description_label = ttk.Label(section, text="Description")
        description_label.pack(anchor=tk.W)
        self.description_text = tk.Text(section, height=4, wrap=tk.WORD)
        self.description_text.pack(fill=tk.X, expand=False, pady=(0, 8))

        abilities_label = ttk.Label(section, text="Abilities / Notes")
        abilities_label.pack(anchor=tk.W)
        self.abilities_text = tk.Text(section, height=4, wrap=tk.WORD)
        self.abilities_text.pack(fill=tk.X, expand=False)

    def _build_custom_stats_section(self, parent: ttk.Frame) -> None:
        section = ttk.LabelFrame(parent, text="Additional Stats", padding=8)
        section.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        entry_frame = ttk.Frame(section)
        entry_frame.pack(fill=tk.X, expand=False, pady=(0, 8))

        ttk.Label(entry_frame, text="Label").grid(row=0, column=0, padx=4, pady=2)
        ttk.Label(entry_frame, text="Value").grid(row=0, column=1, padx=4, pady=2)

        self.custom_label_var = tk.StringVar()
        self.custom_value_var = tk.StringVar()

        label_entry = ttk.Entry(entry_frame, textvariable=self.custom_label_var)
        value_entry = ttk.Entry(entry_frame, textvariable=self.custom_value_var)
        label_entry.grid(row=1, column=0, padx=4, pady=2, sticky="ew")
        value_entry.grid(row=1, column=1, padx=4, pady=2, sticky="ew")
        entry_frame.columnconfigure(0, weight=1)
        entry_frame.columnconfigure(1, weight=1)

        button_frame = ttk.Frame(section)
        button_frame.pack(fill=tk.X, expand=False, pady=(0, 8))

        add_button = ttk.Button(button_frame, text="Add", command=self._add_custom_stat)
        remove_button = ttk.Button(
            button_frame, text="Remove Selected", command=self._remove_custom_stat
        )
        add_button.pack(side=tk.LEFT, padx=(0, 4))
        remove_button.pack(side=tk.LEFT)

        self.custom_tree = ttk.Treeview(
            section,
            columns=("label", "value"),
            show="headings",
            height=5,
        )
        self.custom_tree.heading("label", text="Label")
        self.custom_tree.heading("value", text="Value")
        self.custom_tree.column("label", width=160, anchor=tk.W)
        self.custom_tree.column("value", width=160, anchor=tk.W)
        self.custom_tree.pack(fill=tk.BOTH, expand=True)

    def _build_actions(self, parent: ttk.Frame) -> None:
        section = ttk.Frame(parent)
        section.pack(fill=tk.X, expand=False)

        ttk.Button(section, text="Update Preview", command=self._update_preview).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(section, text="Copy to Clipboard", command=self._copy_to_clipboard).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(section, text="Save to File", command=self._save_to_file).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(section, text="Reset Form", command=self._reset_form).pack(side=tk.LEFT)

    def _add_field(
        self,
        parent: ttk.Widget,
        field_key: str,
        label: str,
        *,
        row: int,
        column: int,
    ) -> None:
        """Helper to add a labelled entry to the grid based form."""

        var = tk.StringVar()
        entry = ttk.Entry(parent, textvariable=var, width=20)

        ttk.Label(parent, text=label).grid(row=row * 2, column=column, padx=4, pady=(0, 2), sticky=tk.W)
        entry.grid(row=row * 2 + 1, column=column, padx=4, pady=(0, 4), sticky="ew")
        parent.grid_columnconfigure(column, weight=1)

        self.fields[field_key] = UnitField(label=label, var=var)

    # ------------------------------------------------------------------
    # Custom stat helpers
    # ------------------------------------------------------------------
    def _add_custom_stat(self) -> None:
        label = self.custom_label_var.get().strip()
        value = self.custom_value_var.get().strip()
        if not label or not value:
            messagebox.showwarning("Missing Data", "Both label and value are required")
            return

        self.custom_stats.append((label, value))
        self.custom_tree.insert("", tk.END, values=(label, value))
        self.custom_label_var.set("")
        self.custom_value_var.set("")
        self._update_preview()

    def _remove_custom_stat(self) -> None:
        selection = self.custom_tree.selection()
        if not selection:
            return

        for item in selection:
            values = self.custom_tree.item(item, "values")
            if values:
                try:
                    self.custom_stats.remove((values[0], values[1]))
                except ValueError:  # pragma: no cover - safe guard
                    pass
            self.custom_tree.delete(item)
        self._update_preview()

    # ------------------------------------------------------------------
    # Preview, export and utilities
    # ------------------------------------------------------------------
    def _load_default_values(self) -> None:
        defaults = {
            "unit_type": "Infantry",
            "category": "Ground",
            "faction": "Neutral",
            "hit_points": "100",
            "armor": "0",
            "damage": "10",
            "range": "5",
            "speed": "1",
            "detection_range": "4",
            "build_time": "60",
            "cost": "100",
        }
        for key, value in defaults.items():
            if key in self.fields:
                self.fields[key].var.set(value)

    def _gather_form_data(self) -> Dict[str, str]:
        data = {key: field.var.get().strip() for key, field in self.fields.items()}
        data["description"] = self._clean_multiline(self.description_text.get("1.0", tk.END))
        data["abilities"] = self._clean_multiline(self.abilities_text.get("1.0", tk.END))
        data["custom_stats"] = self._format_custom_stats()
        return data

    def _clean_multiline(self, text: str) -> str:
        cleaned = text.strip()
        return cleaned.replace("\"", "'")

    def _format_custom_stats(self) -> str:
        if not self.custom_stats:
            return "# Additional stats can be added here"
        lines = ["# Additional Stats"]
        for label, value in self.custom_stats:
            safe_label = label.replace('"', "'")
            safe_value = value.replace('"', "'")
            lines.append(f'{safe_label} "{safe_value}"')
        return "\n".join(lines)

    def _load_template(self) -> str:
        if TEMPLATE_PATH.exists():
            return TEMPLATE_PATH.read_text(encoding="utf-8")
        # Fallback template when the file is missing.
        return (
            "[UNIT] \"{name}\"\n"
            "DisplayName \"{name}\"\n"
            "Category \"{unit_type}\"\n"
            "HitPoints {hit_points}\n"
            "Armor {armor}\n"
            "Damage {damage}\n"
            "Speed {speed}\n"
            "Range {range}\n"
            "DetectionRange {detection_range}\n"
            "BuildTime {build_time}\n"
            "Cost {cost}\n"
            "Description \"{description}\"\n"
            "Abilities \"{abilities}\"\n"
            "{custom_stats}\n"
            "[END]\n"
        )

    def _build_unit_block(self) -> str:
        template = self._load_template()
        data = self._gather_form_data()
        safe_data = SafeDict(data)
        return template.format_map(safe_data)

    def _update_preview(self) -> None:
        block = self._build_unit_block()
        self.preview_text.configure(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", block)
        self.preview_text.configure(state=tk.DISABLED)

    def _copy_to_clipboard(self) -> None:
        block = self._build_unit_block()
        self.root.clipboard_clear()
        self.root.clipboard_append(block)
        messagebox.showinfo("Copied", "The unit definition has been copied to the clipboard")

    def _save_to_file(self) -> None:
        block = self._build_unit_block()
        initial_dir = self._suggest_initial_directory()
        path = filedialog.asksaveasfilename(
            title="Save Unit Definition",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialdir=initial_dir,
            initialfile=f"{self.fields.get('name', UnitField('', tk.StringVar())).var.get() or 'unit'}.txt",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(block)
            messagebox.showinfo("Saved", f"Unit definition saved to:\n{path}")
        except OSError as exc:
            messagebox.showerror("Error", f"Failed to save file:\n{exc}")

    def _suggest_initial_directory(self) -> str:
        units_dir = Path.cwd() / "Units"
        if units_dir.exists():
            return str(units_dir)
        return str(Path.cwd())

    def _reset_form(self) -> None:
        for field in self.fields.values():
            field.var.set("")
        self.description_text.delete("1.0", tk.END)
        self.abilities_text.delete("1.0", tk.END)
        for item in self.custom_tree.get_children():
            self.custom_tree.delete(item)
        self.custom_stats.clear()
        self._load_default_values()
        self._update_preview()


def main() -> None:
    """Entry point used for ``python -m tools.unit_builder.app``."""

    root = tk.Tk()
    app = UnitBuilderApp(root)
    root.mainloop()


if __name__ == "__main__":  # pragma: no cover - manual invocation only
    main()
