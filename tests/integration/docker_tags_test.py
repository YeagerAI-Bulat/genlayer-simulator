import unittest
import subprocess

class TestDockerTags(unittest.TestCase):
    def test_docker_image_tags(self):
        repo = "yeagerai/simulator-jsonrpc"
        tags = subprocess.check_output(["docker", "images", repo, "--format", "{{.Tag}}"]).decode().split()
        self.assertIn("latest", tags)
        with open('version.txt', 'r') as file:
            version = file.read().strip()
        self.assertIn(version, tags)

if __name__ == '__main__':
    unittest.main()