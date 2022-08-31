"""
: title: Simple_Build_Android_Boost;
: 编译android用的cpp boost;
: NDK版本必须 >= 23; boost版本必须 >= 1.76;
: boost version >= 1.77 后, 不需要打文件补丁也正常;
: GNU General Public License v3.0;
: code author: gamefunc, 32686647, https://github.com/gamefunc;
: https://www.gamefunc.top:9029
: win和linux下都可以直接运行;
: 需要设置 ndk_root_path, boost_root_path;
: 免责声明: 任何人可使用该代码, 但要保留以上信息与责任自负;
: andorid的x86和x86_64最好在linxu下构建, 不然某些文件名实在太长win各种悲剧;
: ndk >= 24 不支持 wsl1构建;

:wsl ndk_23:
    进入 cd /mnt/d/Win10FD/OneDrive/1_myCode/Python/C语言相关/android构建boost
        后运行 本 py即可;

    # C:\cpps\ndk\linux\toolchains\llvm\prebuilt\linux-x86_64\bin
        复制clang-12 为 clang 与 clang++, 不然会提示找不到文件,
        原因为自带 clang 与 clang++ 文件为个bash而已;

: 具体步骤看: start_build();
"""

import os, sys, re, shutil, platform, subprocess

if sys.version_info < (3, 8, 0):
    raise TypeError("python版本需要 > 3.8")
"""
c++17 已有:
    "atomic", "chrono", "date_time", 
    "filesystem", "regex", "wave"
"""

class Simple_Build_Android_Boost:
    def __init__(
            self,
            ndk_root_path: str,
            boost_root_path: str,
            arch_list = ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"],
            is_build_log_to_text = False,
            sdk_version = 26,
            with_libs = [],
            without_libs = [
                "python", 
                "atomic", "chrono", "date_time", 
                "filesystem", "regex", "wave",
                "test", "graph", "graph_parallel"],
            build_layout = "system") -> None:
        # 输入参数;
        self.ndk_root_path = ndk_root_path
        self.boost_root_path = boost_root_path
        self.arch_list = arch_list
        self.is_build_log_to_text = is_build_log_to_text
        self.sdk_version = sdk_version
        self.with_libs = with_libs
        self.without_libs = without_libs
        # 不用python;
        if "python" not in self.without_libs:
            self.without_libs.append("python")
        self.build_layout = build_layout



        # 一些编译参数:
        self.target_os = "android"
        self.toolchain = "llvm"
        self.sys_platform = platform.system().lower()
        self.toolset="clang"
        if self.sys_platform == "windows":
            self.clang_exe_name = "clang++.cmd"
            self.ar_exe_name = "ar.exe"
            self.ranlib_exe_name = "ranlib.exe"
        else:
            self.clang_exe_name = "clang++"
            self.ar_exe_name = "ar"
            self.ranlib_exe_name = "ranlib"

        # 输出目录;
        self.boost_build_tmp_dir = os.path.join(
            self.boost_root_path, f"{self.target_os}_build_tmp")
        self.boost_build_prefix_dir = os.path.join(
            self.boost_root_path, self.target_os)


    def start_build(self):
        """
        主运行:
        """
        # 分析ndk目录, compiler_folder_path已把"\\" 替换为 "/";
        self.ndk_version, self.compiler_folder_path = \
            self.__analyze_android_ndk()
        # 分析boost版本;
        self.__analyze_boost_version()
        # 添加编译设置user_jam文件;
        self.__add_user_build_jam()
        # 打补丁: boost 1.76前都打补丁, 1.77后不打没问题;
        # self.__patch_error_code_hpp()
        # self.__patch_filesystem_cpp()
        # self.__patch_common_jam()
        # 编译:
        self.__build()


    def restore_src_from_src_bakup(self):
        """
        编译完毕后把修改过的src文件恢复回去;
        """
        error_code_hpp_path = os.path.join(
            self.boost_root_path, 
            "boost", "system", "error_code.hpp")
        self.__patch_common(error_code_hpp_path)
        path_cpp_path = os.path.join(
            self.boost_root_path, 
            "libs", "filesystem", "src", "path.cpp")
        self.__patch_common(path_cpp_path)
        common_jam_path = os.path.join(
            self.boost_root_path, 
            "tools", "build", "src", "tools", "common.jam")
        self.__patch_common(common_jam_path)


    def __analyze_android_ndk(self) -> tuple:
        """
        获取并设置ndk一些变量;
        ndk_version;
        compiler_folder_path;
        """
        with open(
                os.path.join(self.ndk_root_path, 
                    "source.properties"),
                "r", encoding="utf-8") as f:
            text = f.read()
        
        v = re.findall(r"Pkg.Revision = .*", text)[0].replace(
            "Pkg.Revision =", "")
        ndk_version = float(v.rsplit(".", 1)[0])
        print(f"{ndk_version = }")

        if ndk_version < 23:
            raise ValueError("ndk version must >= 23")
        if self.sdk_version < 26:
            raise ValueError("sdk version must >= 26(>= android 8.0)")

        compiler_folder_path = os.path.join(
            self.ndk_root_path, "toolchains",
            self.toolchain, "prebuilt", 
            f"{self.sys_platform}-x86_64", "bin").replace("\\", "/")
        print(f"{compiler_folder_path = }")
        return (ndk_version, compiler_folder_path)
    

    def __analyze_boost_version(self):
        """
        看看boost版本号:
        """
        version_hpp_path = os.path.join(
            self.boost_root_path, "boost", "version.hpp")
        with open(version_hpp_path, "r", encoding="utf-8") as f:
            txt = f.read()
            ver = re.findall(r'#define BOOST_LIB_VERSION.*"', txt)
            if len(ver) == 0:
                raise TypeError("boost路径错误")
            ver = float(ver[0].strip().rsplit(" ", 1)[-1].replace("_", ".").replace('"', ""))
            print(f"boost_version: {ver}")
            if ver < 1.74:
                raise TypeError("只支持编译 >= 1.74版的boost")


    def __add_user_build_jam(self):
        """
        创建编译时需要的jam;
        """
        user_jam_path = os.path.join(
            self.boost_root_path,
            "tools", "build", "src", "user-config.jam")

        # 各编译文件绝对路径;
        arm64v8a_clang_path = os.path.join(
            self.compiler_folder_path, 
            f"aarch64-linux-android{self.sdk_version}-{self.clang_exe_name}"
        )

        armeabiv7a_clang_path = os.path.join(
            self.compiler_folder_path, 
            f"armv7a-linux-androideabi{self.sdk_version}-{self.clang_exe_name}"
        )

        x86_clang_path = os.path.join(
            self.compiler_folder_path, 
            f"i686-linux-android{self.sdk_version}-{self.clang_exe_name}"
        )

        x8664_clang_path = os.path.join(
            self.compiler_folder_path, 
            f"x86_64-linux-android{self.sdk_version}-{self.clang_exe_name}"
        )

        arm64v8a_prefix = os.path.join(
            self.compiler_folder_path, "aarch64-linux-android"
        )
        armeabiv7a_prefix = os.path.join(
            self.compiler_folder_path, "arm-linux-androideabi"
        )
        x86_prefix = os.path.join(
            self.compiler_folder_path, "i686-linux-android"
        )
        x8664_prefix = os.path.join(
            self.compiler_folder_path, "x86_64-linux-android"
        )

        
        # 公共内容;
        jam_text = "import os ;\n"
        jam_text += f"local arm64v8a_cxx_path = {arm64v8a_clang_path} ;\n"
        jam_text += f"local armeabiv7a_cxx_path = {armeabiv7a_clang_path} ;\n"
        jam_text += f"local x86_cxx_path = {x86_clang_path} ;\n"
        jam_text += f"local x8664_cxx_path = {x8664_clang_path} ;\n\n"

        jam_text += f"local arm64v8a_prefix = {arm64v8a_prefix} ;\n"
        jam_text += f"local armeabiv7a_prefix = {armeabiv7a_prefix} ;\n"
        jam_text += f"local x86_prefix = {x86_prefix} ;\n"
        jam_text += f"local x8664_prefix = {x8664_prefix} ;\n\n\n"

        # 每个arch分别内容, 由于是jam文件, 所以win需要replace "\\";
        for arch in ["arm64v8a", "armeabiv7a", "x86", "x8664"]:
            jam_text += "# -----------------------------------\n"
            jam_text += f"using clang : {arch}\n"
            jam_text += ":\n"
            jam_text += f"$({arch}_cxx_path)\n"
            jam_text += ":\n"
            # 必须要这样写, 不然会 Unescaped special character in argument;
            jam_text += f"<archiver>$({self.compiler_folder_path})/llvm-{self.ar_exe_name}\n"
            jam_text += f"<ranlib>$({self.compiler_folder_path})/llvm-{self.ranlib_exe_name}\n"
            jam_text += "<compileflags>-fPIC\n"
            jam_text += "<compileflags>-ffunction-sections\n"
            jam_text += "<compileflags>-fdata-sections\n"
            jam_text += "<compileflags>-funwind-tables\n"
            jam_text += "<compileflags>-fstack-protector-strong\n"
            jam_text += "<compileflags>-no-canonical-prefixes\n"
            jam_text += "<compileflags>-Wformat\n"
            jam_text += "<compileflags>-Werror=format-security\n"
            jam_text += "<compileflags>-frtti\n"
            jam_text += "<compileflags>-fexceptions\n"
            jam_text += "<compileflags>-DNDEBUG\n"
            jam_text += "<compileflags>-g\n"
            jam_text += "<compileflags>-Oz\n\n"

            if arch == "armeabiv7a":
                jam_text += "<compileflags>-mthumb\n\n"
            jam_text += ";\n\n\n"
        with open(user_jam_path, "wb") as f:
            f.write(jam_text.encode("utf-8"))

    
    def __judge_sep(self, file_abs_path: str, wildcard: bytes) -> bytes:
        """
        判断每行结尾是 b"\r\n"还是b"\n"; 
        实际操作是找到包含wildcard的行, 然后看那行最后是\r\n还是\r还是\n;
        """
        with open(file_abs_path, "rb") as f:
            lines = f.readlines()
            for line in lines:
                if wildcard in line:
                    if line.endswith(b"\r\n"):
                        return b"\r\n"
                    elif line.endswith(b"\r"):
                        return  b"\r"
                    elif line.endswith(b"\n"):
                        return b"\n"
                    else:
                        raise TypeError(
                            f"没有检测该文本是\\r\\n还是\\r还是\\n结尾: {line}")
            raise TypeError(f"{file_abs_path}: 文本内容里没有找到: {wildcard}")


    def __patch_common(self, src_path) -> bytes:
        """
        打path的公共部分; 备份src文件到 .src_bakup;
        返回换行符是b"\r\n"还是b"\n";
        """
        bakup_path = f"{src_path}.src_bakup"
        if not os.path.exists(bakup_path):
            print(f"{bakup_path} 不存在, 已复制一份作为备份")
            shutil.copy(src_path, bakup_path)
        else:
            print(f"使用 {bakup_path} 替换掉 {src_path}")
            shutil.copy(bakup_path, src_path)

        return self.__judge_sep(src_path, b"include")

    
    def __patch_error_code_hpp(self):
        """
        修改boost_root/boost/system/error_code.hpp;
        加上: #include <stdio.h>
        """
        error_code_hpp_path = os.path.join(
            self.boost_root_path, 
            "boost", "system", "error_code.hpp")
        file_sep = self.__patch_common(error_code_hpp_path)
        with open(error_code_hpp_path, "rb") as f:
            tmp = f.read()
        tmp = b"#include <stdio.h>" + file_sep + tmp
        with open(error_code_hpp_path, "wb") as f:
            f.write(tmp)
        print(f"已修改 {error_code_hpp_path}")
    

    def __patch_filesystem_cpp(self):
        """
        修改boost_root/libs/filesystem/src/path.cpp
        有两个地方需要添加: || defined(__ANDROID__), 修改内容与utf-8编码相关;
        # 补丁说明: 属于filesystem, 不使用boost::filesystem的话可以不修改;
        """
        path_cpp_path = os.path.join(
            self.boost_root_path, 
            "libs", "filesystem", "src", "path.cpp")
        file_sep = self.__patch_common(path_cpp_path)
        """
        1
        """
        src_1 = b"# include <windows.h>" + file_sep
        src_1 += b"#elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__) \\" + file_sep
        src_1 += b" || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__HAIKU__)" + file_sep
        src_1 += b"# include <boost/filesystem/detail/utf8_codecvt_facet.hpp>" + file_sep
        src_1 += b"#endif" + file_sep

        out_1 = b"# include <windows.h>"  + file_sep
        out_1 += b"#elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__) \\" + file_sep
        # 尾部添加 "\" ;
        out_1 += b" || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__HAIKU__) \\" + file_sep
        # 主要添加这句;
        out_1 += b" || defined(__ANDROID__)" + file_sep
        out_1 += b"# include <boost/filesystem/detail/utf8_codecvt_facet.hpp>" + file_sep
        out_1 += b"#endif" + file_sep
        """
        2
        """
        src_2 = b"# elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__) \\" + file_sep
        src_2 += b"  || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__HAIKU__)" + file_sep
        src_2 += b'    // "All BSD system functions expect their string parameters to be in UTF-8 encoding' + file_sep
        
        out_2 = b"# elif defined(macintosh) || defined(__APPLE__) || defined(__APPLE_CC__) \\" + file_sep
        # 尾部添加 "\";
        out_2 += b"  || defined(__FreeBSD__) || defined(__OpenBSD__) || defined(__HAIKU__) \\" + file_sep
        # 
        out_2 += b"  || defined(__ANDROID__)" + file_sep
        out_2 += b'    // "All BSD system functions expect their string parameters to be in UTF-8 encoding' + file_sep

        with open(path_cpp_path, "rb") as f:
            tmp = f.read()
        tmp = tmp.replace(src_1, out_1)
        tmp = tmp.replace(src_2, out_2)
        with open(path_cpp_path, "wb") as f:
            f.write(tmp)
        print(f"已修改 {path_cpp_path}")



    def __patch_common_jam(self):
        """
        修改boost_root/tools/build/src/tools/common.jam
        clang编译相关的;
        # 补丁说明: 不判断clang直接: version = $(version[1];
        """
        common_jam_path = os.path.join(
            self.boost_root_path, 
            "tools", "build", "src", "tools", "common.jam")
        file_sep = self.__patch_common(common_jam_path)

        src = b"    # Ditto, from Clang 4" + file_sep
        src += b"    if ( $(tag) = clang || $(tag) = clangw ) && $(version[1]) && [ numbers.less 3 $(version[1]) ]" + file_sep
        src += b"    {" + file_sep
        src += b"        version = $(version[1]) ;" + file_sep

        out = b"    # Ditto, from Clang 4" + file_sep
        # 开头添加 #注释掉该行;
        out += b"    #if ( $(tag) = clang || $(tag) = clangw ) && [ numbers.less 3 $(version[1]) ]" + file_sep
        out += b"    {" + file_sep
        out += b"        version = $(version[1]) ;" + file_sep


        with open(common_jam_path, "rb") as f:
            tmp = f.read()
        tmp = tmp.replace(src, out)
        with open(common_jam_path, "wb") as f:
            f.write(tmp)
        print(f"已修改 {common_jam_path}")


    def __build(self):
        if self.sys_platform == "windows":
            cmd_var = 'echo "pwd: %cd%" && '
        else:
            cmd_var = "pwd && "
        
        
        for arch in self.arch_list:
            os.chdir(self.boost_root_path)
            # 调用bootstrap.bat/sh 去创建b2.exe;
            if self.sys_platform == "windows":
                if not os.path.exists(
                        os.path.join(self.boost_root_path, "b2.exe")):
                    subprocess.call("bootstrap.bat", shell=True)
                    # subprocess.call("bootstrap.bat gcc", shell=True)
                cmd = "b2.exe  "
            else:
                if not os.path.exists(
                        os.path.join(self.boost_root_path, "b2")):
                    subprocess.call("./bootstrap.sh", shell=True)
                cmd = "./b2 "
            # 在第一个错误时立即停止编译, 而不是继续编译;
            cmd += " -q "
            # debug等级
            cmd += " -d+2 "
            # using clang : armeabiv7a; user-config不喜欢 "-", "_"符号;
            jam_arch = arch.replace("-", "").replace("_", "")
            cmd += " --ignore-site-config "
            cmd += f" -j{os.cpu_count()} "
            cmd += f" target-os={self.target_os} "
            cmd += f" toolset={self.toolset}-{jam_arch} "
            cmd += " threading=multi "
            cmd += " link=static "
            # cmd += " runtime-link=static "
            # cmd += " --build-type=complete "
            cmd += f" --layout={self.build_layout} "

            for with_lib in self.with_libs:
                cmd += f" --with-{with_lib} "

            for without_lib in self.without_libs:
                cmd += f" --without-{without_lib} "
        
            build_dir = os.path.join(self.boost_build_tmp_dir, arch)
            cmd += f' --build-dir="{build_dir}" '
            prefix_dir = os.path.join(self.boost_build_prefix_dir, arch)
            cmd += f' --prefix="{prefix_dir}" '

            if self.is_build_log_to_text:
                build_log_abs_path = os.path.join(
                    self.boost_root_path, f"build_log_{arch}.txt")
                # 覆盖一下文件;
                with open(build_log_abs_path, "wb") as f:
                    f.write(b"")
                cmd += f' install -a > "{build_log_abs_path}" 2>&1'
                print(f"build_log将会输出到: {build_log_abs_path}")
            else:
                cmd += f' install -a '

            cmd = cmd_var + cmd
            print(f"\nb2_build_构建命令: {cmd}\n\n开始处理: {arch}")
            subprocess.call(cmd, shell=True)
            print(f"\n\ngamefunc: 处理完毕: {arch};\n\n\n")



def main():
    # 构建直接复到wsl下(nano xx.py即可): 然后 python3 xx.py;
    
    # b = Simple_Build_Android_Boost(
    #     r"C:\Users\feve\AppData\Local\Android\Sdk\ndk\22.1.7171670",
    #     r"L:\0_cpp_plus\boost\boost_1_77_0",
    #     ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
    # )

    b = Simple_Build_Android_Boost(
        "/mnt/c/cpps/ndk/linux",
        "/mnt/c/cpps/libs/boost/boost_1_80_0",
        ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
    )
    b.start_build()
    # b.restore_src_from_src_bakup()

    os.system("pause")

main()
            
        
        

