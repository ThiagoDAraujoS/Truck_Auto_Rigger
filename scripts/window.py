from maya import cmds
from scripts.tuning_panel_widget import create_tuning_panel_widget


class Window:
    """ This class builds a window that controls the arm rigger tool"""
    NAME = "Auto_Rigger_Window"
    UI_BGC = 0.2, 0.2, 0.2
    UI_LIGHT_GRAY = 0.2, 0.2, 0.2
    UI_RED = 0.5, 0.1, 0.1
    UI_GREEN = 0.1, 0.5, 0.1
    UI_BLUE = 0.1, 0.3, 0.5
    SIZE = 350

    def __init__(self, arm_rigging_tool_ref, belt_rigging_tool_ref):
        # Get a reference to the arm rigging tool
        self.bucket_tool_ref = arm_rigging_tool_ref
        self.belt_tool_ref = belt_rigging_tool_ref

    def open_window(self) -> None:
        """ Open the window """
        if cmds.window(Window.NAME, query=True, exists=True):
            cmds.deleteUI(Window.NAME, window=True)
        self.assemble_window()

    def assemble_window(self) -> str:
        """ Assemble the window, then show it """
        # Build a window element
        window_element = cmds.window(Window.NAME, sizeable=False)
        cmds.columnLayout(columnAttach=('both', 0), columnWidth=Window.SIZE + 20, )
        tabs_element = cmds.tabLayout(innerMarginWidth=5, innerMarginHeight=5)

        # Build the first Tab "Bucket tool"
        bucket_tab_element = self.assemble_abstract_tab(self.bucket_tool_ref, self.arm_control_box_widget)
        belt_tab_element = self.assemble_abstract_tab(self.belt_tool_ref, self.belt_control_box_widget)

        # Attach tabs to the tab element
        cmds.tabLayout(tabs_element, edit=True, tabLabel=((bucket_tab_element, 'Bucket'), (belt_tab_element, "Belt")))

        # Show the window
        cmds.showWindow(window_element)
        return window_element

    def belt_control_box_widget(self, print_message, show_icon, enable_tuning_panel):
        """ Creates a custom 'arm rigger widget' that serves as state machine and controls other widgets' features """

        def state(message="", icon=""):
            def inner(function):
                def wrapper(*args, **kwargs):
                    if message:
                        print_message(message)
                    if icon:
                        show_icon(icon)
                    cmds.setParent(root_element)
                    children = cmds.columnLayout(root_element, query=True, childArray=True)
                    if children:
                        cmds.deleteUI(children)
                    function(*args, **kwargs)

                return wrapper

            return inner

        # -------------------------------------------------------------STARTING STATE-------------------------------------------------------------------------------------
        @state(" - Welcome!\n - Press the [Start Building Rig] button to start\n   building your belt rig.", "PxrPtexture.svg")
        def starting_state():
            def on_kickstart_tool(*_):
                enable_tuning_panel(False)
                position_frame_state()
                self.belt_tool_ref.build_core_ctrl()

            cmds.button(label="Start Building Rig", c=on_kickstart_tool, h=127, bgc=Window.UI_GREEN)

        # ------------------------------------------------------------------SETUP LOC STATE--------------------------------------------------------------------------------
        @state(" - I have created a frame.\n - Please place it on top of the model's wheels/gears.\n", "breakTangent.png")
        def position_frame_state():
            def on_reset(*_):
                self.belt_tool_ref.destroy_core_ctrl()
                self.belt_tool_ref.build_core_ctrl()
                position_frame_state()

            def on_apply(*_):
                self.belt_tool_ref.lock_frame_ctrl()
                self.belt_tool_ref.build_circle_ctrls()
                position_wheels_state()

            def on_back(*_):
                self.belt_tool_ref.destroy_core_ctrl()
                enable_tuning_panel(True)
                starting_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset, w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Back", c=on_back, w=63, h=62, bgc=Window.UI_BGC)

        # ---------------------------------------------------------SETUP IK STATE-------------------------------------------------------------------------------------------
        @state(" - Spread these circles on top of each wheel", "breakTangent.png")
        def position_wheels_state():
            def on_reset(*_):
                self.belt_tool_ref.destroy_circle_ctrls()
                self.belt_tool_ref.build_circle_ctrls()
                position_wheels_state()

            def on_apply(*_):
                self.belt_tool_ref.build_belt_ctrl()
                self.belt_tool_ref.build_mash_driver()
                enable_tuning_panel(True)
                starting_state()

            def on_back(*_):
                self.belt_tool_ref.destroy_circle_ctrls()
                self.belt_tool_ref.unlock_frame_ctrl()
                position_frame_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset, w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Back", c=on_back, w=63, h=62, bgc=Window.UI_BGC)

        # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
        root_element = cmds.columnLayout(bgc=Window.UI_LIGHT_GRAY, columnAttach=('both', 0), adjustableColumn=True, )
        starting_state()
        cmds.setParent("..")
        return root_element

    def arm_control_box_widget(self, print_message, show_icon, enable_tuning_panel):
        """ Creates a custom 'arm rigger widget' that serves as state machine and controls other widgets' features """

        def state(message="", icon=""):
            def inner(function):
                def wrapper(*args, **kwargs):
                    if message:
                        print_message(message)
                    if icon:
                        show_icon(icon)
                    cmds.setParent(root_element)
                    children = cmds.columnLayout(root_element, query=True, childArray=True)
                    if children:
                        cmds.deleteUI(children)
                    function(*args, **kwargs)

                return wrapper

            return inner

        # -------------------------------------------------------------STARTING STATE-------------------------------------------------------------------------------------
        @state(" - Welcome!\n - Press the [Start Building Rig] button to start\n   building your arm rig.", "PxrPtexture.svg")
        def starting_state():
            def on_kickstart_tool(*_):
                enable_tuning_panel(False)
                setup_loc_state()
                self.bucket_tool_ref.create_locator()

            cmds.button(label="Start Building Rig", c=on_kickstart_tool, h=127, bgc=Window.UI_GREEN)

        # ------------------------------------------------------------------SETUP LOC STATE--------------------------------------------------------------------------------
        @state(" - I have created some locators.\n - Please move them in the arm's joint positions.\n   In order from the base to the end of the arm", "breakTangent.png")
        def setup_loc_state():
            def on_reset(*_):
                self.bucket_tool_ref.reset_locator()
                self.bucket_tool_ref.create_locator()
                setup_loc_state()

            def on_apply(*_):
                self.bucket_tool_ref.bake_locator_position()
                self.bucket_tool_ref.create_joints()
                setup_ik_state()

            def on_cancel(*_):
                self.bucket_tool_ref.reset_locator()
                enable_tuning_panel(True)
                starting_state()

            cmds.rowLayout(numberOfColumns=1)
            cmds.button(label="Accept", c=on_apply, w=129, h=63, bgc=Window.UI_GREEN)
            cmds.setParent("..")
            cmds.rowLayout(numberOfColumns=2, columnAlign2=["right", "left"], co2=[-1, -1])
            cmds.button(label="Reset", c=on_reset, w=64, h=62, bgc=Window.UI_RED)
            cmds.button(label="Cancel", c=on_cancel, w=63, h=62, bgc=Window.UI_BGC)

        # ---------------------------------------------------------SETUP IK STATE-------------------------------------------------------------------------------------------
        @state(" - Select 2 Joints from the base to the end of the\n   arm in order to build an IK Control", "breakTangent.png")
        def setup_ik_state():
            def on_build_ik(*_):
                self.bucket_tool_ref.create_ik_controllers()

            def on_finish(*_):
                enable_tuning_panel(True)
                starting_state()

            cmds.button(label="Build IK", c=on_build_ik, w=120, h=62, bgc=Window.UI_BLUE)
            cmds.separator()
            cmds.button(label="Finish", c=on_finish, w=120, h=62, bgc=Window.UI_GREEN)

        # -----------------------------------------------------------------------------------------------------------------------------------------------------------------
        root_element = cmds.columnLayout(bgc=Window.UI_LIGHT_GRAY, columnAttach=('both', 0), adjustableColumn=True, )
        starting_state()
        cmds.setParent("..")
        return root_element

    @staticmethod
    def assemble_abstract_tab(target_reference, control_box) -> tuple[str, str, str]:
        """ This method build an abstract tab, it requires a control box method in order to become concrete, so far only arm_control_box_widget can be used as a valid control_box """
        main_element = cmds.formLayout(numberOfDivisions=8, h=Window.SIZE + 4)

        # draw tuning box
        tuning_box_element = cmds.scrollLayout(verticalScrollBarThickness=16, childResizable=True)
        create_tuning_panel_widget(ref=target_reference, label_size=75, columnAttach=('both', 1), adj=True, rs=2, adjustableColumn=True)
        cmds.setParent("..")

        # draw icon box
        image_box_element = cmds.iconTextStaticLabel(st='iconOnly', i='PxrPtexture.svg', l='spotlight', bgc=Window.UI_BGC)

        #  draw prompt box
        prompt_box_element = cmds.text(label=""" - test\n - test\n - test""", ww=True, al="left", font="fixedWidthFont", bgc=Window.UI_BGC)

        # draw button box, and pass the key methods it needs to be able to control the entire tab
        contrl_box_element = control_box(
            lambda text: cmds.text(prompt_box_element, edit=True, label=text),  # This method controls the prompt box's texts
            lambda icon: cmds.iconTextStaticLabel(image_box_element, edit=True, i=icon),  # This method controls the image box's images
            lambda state: cmds.scrollLayout(tuning_box_element, edit=True, enable=state))  # This method controls the tuning box's enabled status

        # attach elements to form
        cmds.formLayout(main_element, edit=True, attachPosition=[
            (prompt_box_element, 'top', 1, 6), (prompt_box_element, 'bottom', 2, 8), (prompt_box_element, 'left', 2, 0), (prompt_box_element, 'right', 2, 8),
            (tuning_box_element, 'top', 1, 0), (tuning_box_element, 'bottom', 1, 6), (tuning_box_element, 'left', 1, 0), (tuning_box_element, 'right', 0, 5),
            (contrl_box_element, 'top', 2, 3), (contrl_box_element, 'bottom', 2, 6), (contrl_box_element, 'left', 2, 5), (contrl_box_element, 'right', 2, 8),
            (image_box_element, 'top', 2, 0), (image_box_element, 'bottom', 1, 3), (image_box_element, 'left', 2, 5), (image_box_element, 'right', 2, 8)])

        # Bounce to parent and return root element
        cmds.setParent('..')
        return main_element
