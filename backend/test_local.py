#!/usr/bin/env python3
"""
Lokaler Test für BackupDocu JSON-Modus
Führe aus: python test_local.py
"""

import subprocess
import time
import requests
import os
import sys

def run_tests():
    print("🚀 Starte BackupDocu lokale Tests (JSON-Modus)...")

    # Set JSON mode
    os.environ['STORAGE_MODE'] = 'json'

    # Start FastAPI server in background
    print("📡 Starte FastAPI Server...")
    proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(__file__))
    time.sleep(5)  # Wait for server to start

    try:
        base_url = 'http://localhost:8000'

        # Test health endpoint
        print("🏥 Teste Health-Check...")
        resp = requests.get(f'{base_url}/api/health')
        assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
        print('✅ Health check passed')

        # Test stats (no config endpoint in JSON-only mode)
        print("📊 Teste Statistiken...")
        resp = requests.get(f'{base_url}/api/stats')
        assert resp.status_code == 200, f"Stats failed: {resp.status_code}"
        stats = resp.json()
        assert 'servers' in stats, "servers not in stats"
        print('✅ Stats endpoint passed')
        print("📊 Teste Statistiken...")
        resp = requests.get(f'{base_url}/api/stats')
        assert resp.status_code == 200, f"Stats failed: {resp.status_code}"
        stats = resp.json()
        assert 'servers' in stats, "servers not in stats"
        assert stats['servers'] == 0, f"Expected 0 servers, got {stats['servers']}"
        print('✅ Stats passed')

        # Test create server
        print("➕ Teste Server-Erstellung...")
        resp = requests.post(f'{base_url}/api/servers',
                           json={'name': 'Test Server', 'hostname': 'test.local'})
        assert resp.status_code == 201, f"Create server failed: {resp.status_code}"
        server = resp.json()
        assert server['name'] == 'Test Server', f"Wrong name: {server.get('name')}"
        print('✅ Create server passed')

        # Test get server
        print("📖 Teste Server-Abruf...")
        resp = requests.get(f'{base_url}/api/servers/{server["id"]}')
        assert resp.status_code == 200, f"Get server failed: {resp.status_code}"
        print('✅ Get server passed')

        # Test update server
        print("✏️ Teste Server-Update...")
        resp = requests.put(f'{base_url}/api/servers/{server["id"]}',
                          json={'name': 'Updated Server', 'hostname': 'updated.local'})
        assert resp.status_code == 200, f"Update server failed: {resp.status_code}"
        updated = resp.json()
        assert updated['name'] == 'Updated Server', f"Wrong updated name: {updated.get('name')}"
        print('✅ Update server passed')

        # Test delete server
        print("🗑️ Teste Server-Löschung...")
        resp = requests.delete(f'{base_url}/api/servers/{server["id"]}')
        assert resp.status_code == 204, f"Delete server failed: {resp.status_code}"
        print('✅ Delete server passed')

        # Test stats after operations
        print("📊 Teste finale Statistiken...")
        resp = requests.get(f'{base_url}/api/stats')
        stats = resp.json()
        assert stats['servers'] == 0, f"Expected 0 servers after delete, got {stats['servers']}"
        print('✅ Final stats check passed')

        print('\n🎉 Alle JSON-Storage-Tests erfolgreich bestanden!')
        return True

    except Exception as e:
        print(f'\n❌ Test fehlgeschlagen: {e}')
        import traceback
        traceback.print_exc()
        return False

    finally:
        print("\n🛑 Stoppe Server...")
        proc.terminate()
        proc.wait()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)