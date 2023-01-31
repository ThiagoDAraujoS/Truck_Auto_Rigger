import sys
import maya.api.OpenMaya as om


def maya_useNewAPI(): pass

class TruckRigger(om.MPxCommand):
    kPluginCmdName = "truck_rigger"

    def __init__(self):
        om.MPxCommand.__init__(self)

    @staticmethod
    def cmdCreator():
        return TruckRigger()

    def doIt(self, args):
        print("Do whatever to load the truck rigger tool")


def initializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    pluginFn.registerCommand(TruckRigger.kPluginCmdName, TruckRigger.cmdCreator)


def uninitializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    pluginFn.deregisterCommand(TruckRigger.kPluginCmdName)

