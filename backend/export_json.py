import sys
from pathlib import Path
import json

# Add backend directory to PYTHONPATH
backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.main import get_provinces, get_ablation, get_stability, get_geojson
from fastapi.encoders import jsonable_encoder

def export_all():
    # Target directory in frontend public/api
    public_api_dir = backend_dir.parent / "dashboard-vue" / "public" / "api"
    public_api_dir.mkdir(parents=True, exist_ok=True)
    
    # Mapping of filenames to endpoint functions
    endpoints = {
        "provinces.json": get_provinces,
        "ablation.json": get_ablation,
        "stability.json": get_stability,
        "geojson.json": get_geojson
    }
    
    for filename, func in endpoints.items():
        print(f"Exporting {filename}...")
        try:
            data = func()
            json_data = jsonable_encoder(data)
            output_file = public_api_dir / filename
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            print(f"Successfully exported to {output_file}")
        except Exception as e:
            print(f"Error exporting {filename}: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == "__main__":
    export_all()
