from conans import ConanFile
from conans import tools
import platform, os


class BoostConan(ConanFile):
    name = "boost"
    version = "1.59.0"

    tag = "boost-{}".format(version)
    source_dir = tag

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "header_only": [True, False]}
    default_options = "shared=True", "header_only=False"
    counter_config = 0
    git_url = "https://github.com/boostorg/boost.git"
    url = "https://github.com/owbone/conan-boost"

    def config(self):
        # If header only, the compiler, etc, does not affect the package!
        self.counter_config += 1
        # config is called twice, one before receive the upper dependencies and another before
        if self.options.header_only and self.counter_config==2:
            self.output.info("HEADER ONLY")
            self.settings.clear()
            self.options.remove("shared")
        if not self.options.header_only \
           and self.settings.os == "Windows" \
           and "MT" in str(self.settings.compiler.runtime):
            self.options.shared = False

    def source(self):
        self.run("git clone --recursive --branch {} {} {}".format(self.tag, self.git_url, self.source_dir))

    def build(self):
        if self.options.header_only:
            return

        command = "bootstrap" if self.settings.os == "Windows" else "./bootstrap.sh"
        try:
            self.run("cd {} && {}".format(self.source_dir, command))
        except:
            self.run(
                "cd {} && type bootstrap.log".format(self.source_dir)
                if self.settings.os == "Windows"
                else "cd {} && cat bootstrap.sh".format(self.source_dir)
            )
            raise

        toolset_map = {"Visual Studio": "msvc-12.0"}
        toolset = toolset_map.get(self.settings.compiler, self.settings.compiler)

        flags = ["toolset={}".format(toolset)]
        flags.append("link=%s" % ("static" if not self.options.shared else "shared"))
        if self.settings.compiler == "Visual Studio" and self.settings.compiler.runtime:
            flags.append("runtime-link=%s" % ("static" if "MT" in str(self.settings.compiler.runtime) else "shared"))
        flags.append("variant=%s" % str(self.settings.build_type).lower())
        flags.append("address-model=%s" % ("32" if self.settings.arch == "x86" else "64"))
        b2_flags = " ".join(flags)

        command = "b2" if self.settings.os == "Windows" else "./b2"
        full_command = "cd {} && {} {} -j8 --abbreviate-paths --without-python".format(self.source_dir, command, b2_flags)
        self.output.warn(full_command)
        self.run(full_command)

    def package(self):
        self.copy(pattern="*", dst="include/boost", src="{}/boost".format(self.source_dir))
        self.copy(pattern="*.so.*", dst="lib", src="{}/stage/lib".format(self.source_dir))
        self.copy(pattern="*.dylib*", dst="lib", src="{}/stage/lib".format(self.source_dir))
        self.copy(pattern="*.lib", dst="lib", src="{}/stage/lib".format(self.source_dir))
        self.copy(pattern="*.dll", dst="bin", src="{}/stage/lib".format(self.source_dir))

    def package_info(self):
        if not self.options.header_only and self.options.shared:
            self.cpp_info.defines.append("BOOST_DYN_LINK")

        libs = ("atomic chrono container context coroutine date_time exception filesystem "
                "graph iostreams locale log_setup log math_c99 math_c99f math_c99l math_tr1 "
                "math_tr1f math_tr1l prg_exec_monitor program_options random regex serialization "
                "signals system test_exec_monitor thread timer unit_test_framework wave "
                "wserialization").split()
        if not self.options.header_only and self.settings.os != "Windows":
            self.cpp_info.libs.extend(["boost_%s" % lib for lib in libs])
