"""Debug passo a passo do snapshot"""
print("\n" + "="*70)
print("🔍 DEBUG PASSO A PASSO DO SNAPSHOT")
print("="*70)

# Passo 1: Importar gateways
print("\n[1] Importando gateways...")
try:
    from core.gateways import avd_manager, emulator_ctl
    print("✅ Gateways importados")
except Exception as e:
    print(f"❌ Erro ao importar: {e}")
    exit(1)

# Passo 2: Listar AVDs
print("\n[2] Listando AVDs disponíveis...")
try:
    avds = avd_manager.listar_avds()
    print(f"✅ Encontrados {len(avds)} AVDs:")
    for avd in avds:
        print(f"   - {avd}")
    
    if len(avds) == 0:
        print("\n⚠️  PROBLEMA: Nenhum AVD encontrado!")
        print("   Crie um AVD via Android Studio ou:")
        print("   avdmanager create avd -n teste -k 'system-images;android-33;google_apis;x86_64'")
        
except Exception as e:
    print(f"❌ Erro ao listar AVDs: {e}")
    import traceback
    traceback.print_exc()

# Passo 3: Listar emuladores ativos
print("\n[3] Listando emuladores rodando...")
try:
    ativos = emulator_ctl.listar_emuladores_ativos()
    print(f"✅ Encontrados {len(ativos)} emuladores rodando:")
    for serial in ativos:
        print(f"   - {serial}")
    
    if len(ativos) == 0:
        print("\n⚠️  PROBLEMA: Nenhum emulador rodando!")
        print("   Inicie um emulador:")
        print("   emulator -avd Medium_Phone_API_36.1 -port 5560 &")
        
except Exception as e:
    print(f"❌ Erro ao listar ativos: {e}")
    import traceback
    traceback.print_exc()

# Passo 4: Verificar normalização de porta
print("\n[4] Testando normalização de porta...")
try:
    from core.utils import normalizar_porta_console
    
    test_ports = [5560, 5561, 5562, 5563]
    for p in test_ports:
        normalized = normalizar_porta_console(p)
        print(f"   {p} -> {normalized} {'✅ (par)' if normalized % 2 == 0 else '❌ (ímpar)'}")
        
except Exception as e:
    print(f"❌ Erro na normalização: {e}")

# Passo 5: Simular algoritmo do snapshot
print("\n[5] Simulando algoritmo do snapshot original...")
try:
    from core.utils import normalizar_porta_console
    
    avds_sorted = sorted(avds if 'avds' in locals() else [])
    running = set(ativos if 'ativos' in locals() else [])
    base = normalizar_porta_console(5560)
    
    print(f"   Base: {base}")
    print(f"   AVDs ordenados: {avds_sorted}")
    print(f"   Running: {running}")
    
    print("\n   Mapeamento:")
    for i, name in enumerate(avds_sorted):
        port = base + (2 * i)
        serial = f"emulator-{port}"
        status = "Rodando" if serial in running else "Desligado"
        match = "✅" if serial in running else "❌"
        print(f"   [{i}] {name} -> porta {port} -> {serial} -> {status} {match}")
        
except Exception as e:
    print(f"❌ Erro na simulação: {e}")
    import traceback
    traceback.print_exc()

# Passo 6: Testar snapshot real
print("\n[6] Testando snapshot real...")
try:
    from core.facade import core
    
    snap = core.emulators.snapshot()
    print(f"✅ Snapshot retornou {len(snap)} dispositivos:")
    
    for s in snap:
        print(f"   - AVD: {s.avd}")
        print(f"     Serial: {s.serial}")
        print(f"     Porta: {s.port}")
        print(f"     Status: {s.status}")
        
    if len(snap) == 0:
        print("\n⚠️  Snapshot está vazio!")
        
except Exception as e:
    print(f"❌ Erro no snapshot: {e}")
    import traceback
    traceback.print_exc()

# Resumo
print("\n" + "="*70)
print("📊 RESUMO")
print("="*70)
if 'avds' in locals() and 'ativos' in locals():
    print(f"AVDs disponíveis: {len(avds)}")
    print(f"Emuladores rodando: {len(ativos)}")
    
    if len(avds) == 0:
        print("\n❌ CAUSA: Nenhum AVD criado no sistema")
        print("   SOLUÇÃO: Crie AVDs via Android Studio")
    elif len(ativos) == 0:
        print("\n❌ CAUSA: Nenhum emulador rodando")
        print("   SOLUÇÃO: emulator -avd <nome_avd> -port 5560 &")
    else:
        print("\n✅ Dados disponíveis, verificar mapeamento de portas")
        
print("="*70 + "\n")