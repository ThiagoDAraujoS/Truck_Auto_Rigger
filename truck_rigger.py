import maya.api.OpenMaya as om
import scripts.arm_rig_builder as arm_rig_builder
import scripts.window as window_script
import scripts.controller_importer as importer

from maya import cmds
import os.path


def maya_useNewAPI(): pass


class TruckRigger(om.MPxCommand):
    kPluginCmdName = "truck_rigger"

    def __init__(self):
        om.MPxCommand.__init__(self)

    @staticmethod
    def cmdCreator():
        return TruckRigger()

    def doIt(self, args):
        tool = arm_rig_builder.ArmRigBuilder()
        window = window_script.Window(tool)
        window.open_window()


def initializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    pluginFn.registerCommand(TruckRigger.kPluginCmdName, TruckRigger.cmdCreator)


def uninitializePlugin(plugin):
    pluginFn = om.MFnPlugin(plugin)
    pluginFn.deregisterCommand(TruckRigger.kPluginCmdName)
