def main_app():
    from kmpc import kmpcapp
    kmpcapp.KmpcApp().run()

def manager_app():
    from kmpc import kmpcmanager
    kmpcmanager.ManagerApp().run()
