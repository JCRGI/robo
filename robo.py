from core.adb_manager import AdbManager


def main():
    adb = AdbManager()
    adb.connect_device()
    output = adb.run_shell("echo 'Olá, mundo Android!'")
    print(output)
    adb.capture_screen()


if __name__ == "__main__":
    main()
