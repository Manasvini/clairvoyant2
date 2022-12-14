# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from . import clairvoyant_meta_pb2 as clairvoyant__meta__pb2


class MetadataServerStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.handleRequest = channel.unary_unary(
                '/clairvoyantmeta.MetadataServer/handleRequest',
                request_serializer=clairvoyant__meta__pb2.Request.SerializeToString,
                response_deserializer=clairvoyant__meta__pb2.Response.FromString,
                )


class MetadataServerServicer(object):
    """Missing associated documentation comment in .proto file."""

    def handleRequest(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_MetadataServerServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'handleRequest': grpc.unary_unary_rpc_method_handler(
                    servicer.handleRequest,
                    request_deserializer=clairvoyant__meta__pb2.Request.FromString,
                    response_serializer=clairvoyant__meta__pb2.Response.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'clairvoyantmeta.MetadataServer', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class MetadataServer(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def handleRequest(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/clairvoyantmeta.MetadataServer/handleRequest',
            clairvoyant__meta__pb2.Request.SerializeToString,
            clairvoyant__meta__pb2.Response.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
