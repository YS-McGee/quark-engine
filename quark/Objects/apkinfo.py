# This file is part of Quark Engine - https://quark-engine.rtfd.io
# See GPLv3 for copying permission.
import hashlib
import os

from androguard.misc import AnalyzeAPK

from quark.Objects.bytecodeobject import BytecodeObject
from quark.utils import tools


class Apkinfo:
    """Information about apk based on androguard analysis"""

    def __init__(self, apk_filepath):
        """Information about apk based on androguard analysis"""
        # return the APK, list of DalvikVMFormat, and Analysis objects
        self.apk, self.dalvikvmformat, self.analysis = AnalyzeAPK(apk_filepath)
        self.apk_filename = os.path.basename(apk_filepath)
        self.apk_filepath = apk_filepath

    def __repr__(self):
        return f"<Apkinfo-APK:{self.apk_filename}>"

    @property
    def filename(self):
        """
        Return the filename of apk.

        :return: a string of apk filename
        """
        return os.path.basename(self.apk_filepath)

    @property
    def filesize(self):
        """
        Return the file size of apk file by bytes.

        :return: a number of size bytes
        """
        return os.path.getsize(self.apk_filepath)

    @property
    def md5(self):
        """
        Return the md5 checksum of the apk file.

        :return: a string of md5 checksum of the apk file
        """
        md5 = hashlib.md5()
        with open(self.apk_filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    @property
    def permissions(self):
        """
        Return all permissions from given APK.

        :return: a list of all permissions
        """
        return self.apk.get_permissions()

    def find_method(self, class_name=".*", method_name=".*", descriptor=None):
        """
        Find method from given class_name and method_name,
        default is find all method.

        :param descriptor:
        :param class_name: the class name of the Android API
        :param method_name: the method name of the Android API
        :return: a generator of MethodClassAnalysis
        """

        regex_method_name = f"^{method_name}$"

        if descriptor is not None:

            des = descriptor.replace(")", "\)").replace("(", "\(")

            result = self.analysis.find_methods(class_name, regex_method_name, descriptor=des)

            if list(result):
                return self.analysis.find_methods(class_name, regex_method_name, descriptor=des)
            else:
                return None
        else:

            result = self.analysis.find_methods(class_name, regex_method_name)

            if list(result):
                return self.analysis.find_methods(class_name, regex_method_name)
            else:
                return None

    def upperfunc(self, class_name, method_name):
        """
        Return the upper level method from given class name and
        method name.

        :param class_name: the class name of the Android API
        :param method_name: the method name of the Android API
        :return: a list of all upper functions
        """

        upperfunc_result = []
        method_set = self.find_method(class_name, method_name)

        if method_set is not None:
            for method in method_set:
                for _, call, _ in method.get_xref_from():
                    # Call is the MethodAnalysis in the androguard
                    # call.class_name, call.name, call.descriptor
                    upperfunc_result.append(call)

            return tools.remove_dup_list(upperfunc_result)

        return None

    def get_method_bytecode(self, class_name, method_name):
        """
        Return the corresponding bytecode according to the
        given class name and method name.

        :param class_name: the class name of the Android API
        :param method_name: the method name of the Android API
        :return: a generator of all bytecode instructions
        """

        result = self.analysis.find_methods(class_name, method_name)

        if list(result):
            for method in self.analysis.find_methods(class_name, method_name):
                try:
                    for _, ins in method.get_method().get_instructions_idx():
                        bytecode_obj = None
                        reg_list = []

                        # count the number of the registers.
                        length_operands = len(ins.get_operands())
                        if length_operands == 0:
                            # No register, no parameter
                            bytecode_obj = BytecodeObject(
                                ins.get_name(), None, None,
                            )
                        elif length_operands == 1:
                            # Only one register

                            reg_list.append(
                                f"v{ins.get_operands()[length_operands - 1][1]}",
                            )
                            bytecode_obj = BytecodeObject(
                                ins.get_name(), reg_list, None,
                            )
                        elif length_operands >= 2:
                            # the last one is parameter, the other are registers.

                            parameter = ins.get_operands()[length_operands - 1]
                            for i in range(0, length_operands - 1):
                                reg_list.append(
                                    "v" + str(ins.get_operands()[i][1]),
                                )
                            if len(parameter) == 3:
                                # method or value
                                parameter = parameter[2]
                            else:
                                # Operand.OFFSET
                                parameter = parameter[1]

                            bytecode_obj = BytecodeObject(
                                ins.get_name(), reg_list, parameter,
                            )

                        yield bytecode_obj
                except AttributeError as error:
                    # TODO Log the rule here
                    continue
