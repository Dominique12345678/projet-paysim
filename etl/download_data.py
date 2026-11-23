"""
Script de téléchargement du dataset PaySim via kagglehub.
Télécharge les fichiers et copie/déplace le CSV dans le dossier data/.
"""

import os
import shutil
import kagglehub

print("🔄 Téléchargement du dataset PaySim depuis Kaggle via kagglehub...")
path = kagglehub.dataset_download("ealaxi/paysim1")
print(f"✅ Téléchargement terminé dans le cache : {path}")

# Trouver le fichier CSV téléchargé
data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(data_dir, exist_ok=True)

csv_files = [f for f in os.listdir(path) if f.endswith(".csv")]
print(f"Fichiers trouvés : {csv_files}")

for csv_file in csv_files:
    src = os.path.join(path, csv_file)
    dst = os.path.join(data_dir, "paysim.csv")
    print(f"Copie de {src} vers {dst}...")
    shutil.copy2(src, dst)
    print(f"✅ Fichier disponible dans : {dst} (Taille : {os.path.getsize(dst) / (1024*1024):.2f} Mo)")
