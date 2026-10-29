if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from lynowcut.self_test import run
        run(sys.argv[2])
    else:
        from lynowcut.app import main
        main()
