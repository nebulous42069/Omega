if __name__ == '__main__':
    import sys
    from resources.libs.common import router

    _handle = int(sys.argv[1])
    _params = sys.argv[2][1:]
    
    dispatcher = router.Router()
    dispatcher.dispatch(_handle, _params)
