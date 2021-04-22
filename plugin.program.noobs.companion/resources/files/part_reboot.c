#include <linux/reboot.h>
#include <sys/syscall.h>
#include <signal.h>
#include <stdlib.h>

int main(int argc, char *argv[])  {
    char *param = NULL;
    int cmd;
    
    if(argc == 2) {
        param = argv[1];
        cmd = LINUX_REBOOT_CMD_RESTART2;
    }
    else {
        cmd = LINUX_REBOOT_CMD_RESTART;
    }

    sync();
    system("/etc/init.d/rcK || /etc/init.d/rc 0");

    sync();
    syscall(SYS_reboot, LINUX_REBOOT_MAGIC1, LINUX_REBOOT_MAGIC2, cmd, param);
    
    return 0;
}
