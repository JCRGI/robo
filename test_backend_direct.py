"""Teste direto do backend - bypass do Flask"""
from core.facade import core

print("\n" + "="*70)
print("🔍 TESTE DIRETO DO BACKEND")
print("="*70)

# Teste direto do snapshot
print("\n[1] Chamando core.emulators.snapshot()...")
try:
    snap = core.emulators.snapshot()
    print(f"✅ Snapshot retornou: {len(snap)} dispositivos")
    
    if len(snap) == 0:
        print("\n⚠️  PROBLEMA: Snapshot está vazio!")
        print("   Vamos investigar cada componente...")
        
        # Teste o ADB diretamente
        print("\n[2] Testando ADB diretamente...")
        devices = core.emulators.adb.list_devices()
        print(f"   ADB list_devices(): {len(devices)} dispositivos")
        for dev in devices:
            print(f"   - {dev}")
        
        # Teste o AVD Manager
        print("\n[3] Testando AVD Manager...")
        avds = core.emulators.avd_mgr.list_avds()
        print(f"   AVD Manager list_avds(): {len(avds)} AVDs")
        for avd in avds:
            print(f"   - {avd}")
            
    else:
        print("\n✅ Dispositivos encontrados:")
        for i, s in enumerate(snap):
            print(f"\n[{i+1}] Dispositivo:")
            print(f"   AVD: {s.avd}")
            print(f"   Serial: {s.serial}")
            print(f"   Porta: {s.port}")
            print(f"   Status: {s.status}")
            print(f"   ABI: {s.abi}")
            print(f"   API Level: {s.api_level}")
            
except Exception as e:
    print(f"❌ ERRO no snapshot: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*70)