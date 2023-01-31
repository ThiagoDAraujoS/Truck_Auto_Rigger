from maya import cmds
from os import path

PLUGIN_FOLDER = path.normpath(path.join(path.dirname(cmds.pluginInfo("truck_rigger.py", path=True, query=True)), "controllers"))


class ImportSpecifications:
    def __init__(self, filepath, lose_nodes):
        self.FILEPATH: str = filepath
        self.LOSE_NODE_NAMES: list[str] = lose_nodes


gear_specifications = ImportSpecifications(path.join(PLUGIN_FOLDER, 'Gear_Controller.mb'), ["CtrlShape_Size_Multiplier"])


class CtrlImporter:
    TEMP_IMPORT_GROUP_NAME = "ar_temp_import"

    def import_ctrl(self, prefix: str, destiny_group: str, specifications: ImportSpecifications) -> tuple[str, str]:
        """ Imports a control curve from an MA file, rename it and set it up to exist in the new rig

            :return: control locator name, control art parent"""

        # Import file
        cmds.file(specifications.FILEPATH, i=True, gr=True, gn=CtrlImporter.TEMP_IMPORT_GROUP_NAME)

        # Select imported object's parents and save their names
        cmds.select(CtrlImporter.TEMP_IMPORT_GROUP_NAME)
        ctrl, ctrl_art  = cmds.listRelatives()

        # Select all imported objects
        cmds.select(CtrlImporter.TEMP_IMPORT_GROUP_NAME)
        cmds.select(cmds.listRelatives(), hi=True)

        # Add a prefix to them
        for asset in cmds.ls(sl=True)+specifications.LOSE_NODE_NAMES:
            cmds.select(asset)
            cmds.rename(f"{prefix}_{asset}", ignoreShape=True)

        # Regroup them
        cmds.select(CtrlImporter.TEMP_IMPORT_GROUP_NAME)
        cmds.ungroup(CtrlImporter.TEMP_IMPORT_GROUP_NAME)
        if destiny_group:
            cmds.parent(cmds.ls(sl=True), destiny_group)
        return ctrl, ctrl_art
