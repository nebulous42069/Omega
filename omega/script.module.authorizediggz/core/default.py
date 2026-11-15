if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'resources'))
    from libs.common import router

    _handle = int(sys.argv[1])
    _params = sys.argv[2][1:]
    
    dispatcher = router.Router()
    dispatcher.dispatch(_handle, _params)
