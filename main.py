if __name__ == '__main__':
    import sys
    if len(sys.argv) == 3 and sys.argv[1] == '--self-test':
        from pathlib import Path
        import traceback
        try:
            from lynowcut.self_test import run
            run(sys.argv[2])
        except BaseException:
            folder = Path(sys.argv[2]); folder.mkdir(parents=True, exist_ok=True)
            (folder / 'self-test-error.txt').write_text(traceback.format_exc(), encoding='utf-8')
            sys.exit(1)
    else:
        from lynowcut.app import main
        main()
