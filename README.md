# Simple_Build_Android_Boost
Simple_Build_Android_Boost


rewrite main():

def main():
    b = Simple_Build_Android_Boost(
        "/mnt/c/cpps/ndk/linux",
        "/mnt/c/cpps/libs/boost/boost_1_80_0",
        ["arm64-v8a", "armeabi-v7a", "x86", "x86_64"]
    )
    b.start_build()

    os.system("pause")
    

python3 Simple_Build_Android_Boost.py
