import argparse

from rhythm_api.auth import issue_JWT

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--sub', type=str, required=True, help='Specify a subject for the claim')
    parser.add_argument('--expires_in', type=int, required=False, help='TTL of token in seconds')

    args = parser.parse_args()

    token = issue_JWT(sub=args.sub, expires_in=args.expires_in)

    print(token)
