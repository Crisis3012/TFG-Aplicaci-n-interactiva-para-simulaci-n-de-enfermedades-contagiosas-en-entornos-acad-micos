from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
import shutil

from backend.faculty import Faculty


class FacultyProjectManager:
    REQUIRED_FILES = {
        "faculty_config.json",
        "nodes.csv",
        "schedules.csv",
    }

    def __init__(self, base_folder: str | Path = "Facultades"):
        self.base_folder = Path(base_folder)
        self.base_folder.mkdir(parents=True, exist_ok=True)

        self.state_path = self.base_folder / "app_state.json"

    # ============================================================
    # Facultades / carpetas
    # ============================================================

    def list_faculties(self) -> list[str]:
        """
        Devuelve solo las carpetas que ya tienen el formato nuevo válido.
        Así evitamos que una carpeta antigua o vacía rompa el arranque.
        """
        return sorted([
            item.name
            for item in self.base_folder.iterdir()
            if item.is_dir() and self.is_valid_faculty_folder(item)
        ])

    def list_all_faculty_folders(self) -> list[str]:
        """
        Devuelve todas las carpetas, aunque no tengan todavía el formato nuevo.
        Puede servir más adelante para migraciones/importaciones.
        """
        return sorted([
            item.name
            for item in self.base_folder.iterdir()
            if item.is_dir()
        ])

    def is_valid_faculty_folder(self, folder_path: str | Path) -> bool:
        folder_path = Path(folder_path)

        if not folder_path.exists() or not folder_path.is_dir():
            return False

        return all(
            (folder_path / filename).exists()
            for filename in self.REQUIRED_FILES
        )

    def get_faculty_path(self, faculty_name: str) -> Path:
        return self.base_folder / faculty_name

    # ============================================================
    # App state / última facultad activa
    # ============================================================

    def get_active_faculty_path(self) -> Optional[Path]:
        if not self.state_path.exists():
            return None

        try:
            with self.state_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None

        raw_path = data.get("active_faculty_path")
        if not raw_path:
            return None

        path = Path(raw_path)

        if not self.is_valid_faculty_folder(path):
            return None

        return path

    def set_active_faculty_path(self, folder_path: str | Path) -> None:
        folder_path = Path(folder_path)

        data = {
            "active_faculty_path": str(folder_path)
        }

        with self.state_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    # ============================================================
    # Crear / cargar / guardar
    # ============================================================

    def create_faculty(self, faculty_name: str, overwrite_if_empty: bool = False) -> Path:
        faculty_name = faculty_name.strip()

        if not faculty_name:
            raise ValueError("El nombre de la facultad no puede estar vacío.")

        folder_path = self.get_faculty_path(faculty_name)

        if folder_path.exists():
            if not folder_path.is_dir():
                raise ValueError(f"Ya existe un archivo llamado '{faculty_name}'.")

            if self.is_valid_faculty_folder(folder_path):
                raise ValueError(f"Ya existe una facultad llamada '{faculty_name}'.")

            if any(folder_path.iterdir()) and not overwrite_if_empty:
                raise ValueError(
                    f"La carpeta '{faculty_name}' ya existe, pero no tiene el formato nuevo de facultad."
                )

        folder_path.mkdir(parents=True, exist_ok=True)

        faculty = Faculty()
        faculty.update_faculty_properties(name=faculty_name)
        faculty.save_to_folder(folder_path)

        self.set_active_faculty_path(folder_path)

        return folder_path

    def ensure_default_faculty(self) -> tuple[Faculty, str]:
        """
        Crea una facultad Pruebas válida si no hay ninguna facultad válida.
        Si ya existe una carpeta Pruebas vacía, la reutiliza.
        Si existe Pruebas con archivos antiguos, crea Pruebas_1, Pruebas_2, etc.
        """
        base_name = "Pruebas"
        folder_path = self.get_faculty_path(base_name)

        if not folder_path.exists():
            created_path = self.create_faculty(base_name)
            return Faculty.load_from_folder(created_path), created_path.name

        if self.is_valid_faculty_folder(folder_path):
            self.set_active_faculty_path(folder_path)
            return Faculty.load_from_folder(folder_path), base_name

        # Si Pruebas existe pero está vacía, la convertimos al formato nuevo.
        if folder_path.is_dir() and not any(folder_path.iterdir()):
            created_path = self.create_faculty(base_name, overwrite_if_empty=True)
            return Faculty.load_from_folder(created_path), created_path.name

        # Si Pruebas existe pero tiene archivos antiguos, no la tocamos.
        # Creamos una nueva carpeta válida.
        index = 1
        while True:
            candidate_name = f"{base_name}_{index}"
            candidate_path = self.get_faculty_path(candidate_name)

            if not candidate_path.exists():
                created_path = self.create_faculty(candidate_name)
                return Faculty.load_from_folder(created_path), candidate_name

            index += 1

    def load_faculty(self, faculty_name: str) -> Faculty:
        folder_path = self.get_faculty_path(faculty_name)

        if not self.is_valid_faculty_folder(folder_path):
            raise FileNotFoundError(
                f"La carpeta '{faculty_name}' no tiene una estructura de facultad válida."
            )

        return Faculty.load_from_folder(folder_path)

    def save_faculty(self, faculty: Faculty, faculty_name: str) -> None:
        folder_path = self.get_faculty_path(faculty_name)
        folder_path.mkdir(parents=True, exist_ok=True)

        faculty.save_to_folder(folder_path)
        self.set_active_faculty_path(folder_path)

    def load_active_or_create_default(self) -> tuple[Faculty, str]:
        """
        Arranque robusto:
        - si hay app_state válido, carga esa facultad;
        - si no, busca la primera facultad válida;
        - si no hay ninguna válida, crea una nueva.
        """
        active_path = self.get_active_faculty_path()

        if active_path is not None:
            return Faculty.load_from_folder(active_path), active_path.name

        valid_faculties = self.list_faculties()

        if valid_faculties:
            faculty_name = valid_faculties[0]
            faculty_path = self.get_faculty_path(faculty_name)

            self.set_active_faculty_path(faculty_path)
            return Faculty.load_from_folder(faculty_path), faculty_name

        return self.ensure_default_faculty()
    
    # ============================================================
    # Eliminar 
    # ============================================================

    def delete_faculty(self, faculty_name: str) -> None:
        faculty_path = self.get_faculty_path(faculty_name)

        if not faculty_path.exists():
            raise FileNotFoundError(f"No existe la facultad: {faculty_name}")

        if not faculty_path.is_dir():
            raise ValueError("La ruta de la facultad no es una carpeta.")

        shutil.rmtree(faculty_path)

        active_path = self.get_active_faculty_path()

        if active_path is not None and active_path.resolve() == faculty_path.resolve():
            remaining_faculties = self.list_faculties()

            if remaining_faculties:
                new_active_path = self.get_faculty_path(remaining_faculties[0])
                self.set_active_faculty_path(new_active_path)
            else:
                self.clear_active_faculty_path()