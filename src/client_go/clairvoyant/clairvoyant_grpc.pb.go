// Code generated by protoc-gen-go-grpc. DO NOT EDIT.

package clairvoyant

import (
	context "context"
	grpc "google.golang.org/grpc"
	codes "google.golang.org/grpc/codes"
	status "google.golang.org/grpc/status"
)

// This is a compile-time assertion to ensure that this generated file
// is compatible with the grpc package it is being compiled against.
// Requires gRPC-Go v1.32.0 or later.
const _ = grpc.SupportPackageIsVersion7

// MonitoringServerClient is the client API for MonitoringServer service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type MonitoringServerClient interface {
	HandleUpdateRequest(ctx context.Context, in *UpdateRequest, opts ...grpc.CallOption) (*StatusReply, error)
}

type monitoringServerClient struct {
	cc grpc.ClientConnInterface
}

func NewMonitoringServerClient(cc grpc.ClientConnInterface) MonitoringServerClient {
	return &monitoringServerClient{cc}
}

func (c *monitoringServerClient) HandleUpdateRequest(ctx context.Context, in *UpdateRequest, opts ...grpc.CallOption) (*StatusReply, error) {
	out := new(StatusReply)
	err := c.cc.Invoke(ctx, "/clairvoyant.MonitoringServer/HandleUpdateRequest", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// MonitoringServerServer is the server API for MonitoringServer service.
// All implementations must embed UnimplementedMonitoringServerServer
// for forward compatibility
type MonitoringServerServer interface {
	HandleUpdateRequest(context.Context, *UpdateRequest) (*StatusReply, error)
	mustEmbedUnimplementedMonitoringServerServer()
}

// UnimplementedMonitoringServerServer must be embedded to have forward compatible implementations.
type UnimplementedMonitoringServerServer struct {
}

func (UnimplementedMonitoringServerServer) HandleUpdateRequest(context.Context, *UpdateRequest) (*StatusReply, error) {
	return nil, status.Errorf(codes.Unimplemented, "method HandleUpdateRequest not implemented")
}
func (UnimplementedMonitoringServerServer) mustEmbedUnimplementedMonitoringServerServer() {}

// UnsafeMonitoringServerServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to MonitoringServerServer will
// result in compilation errors.
type UnsafeMonitoringServerServer interface {
	mustEmbedUnimplementedMonitoringServerServer()
}

func RegisterMonitoringServerServer(s grpc.ServiceRegistrar, srv MonitoringServerServer) {
	s.RegisterService(&MonitoringServer_ServiceDesc, srv)
}

func _MonitoringServer_HandleUpdateRequest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(UpdateRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(MonitoringServerServer).HandleUpdateRequest(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/clairvoyant.MonitoringServer/HandleUpdateRequest",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(MonitoringServerServer).HandleUpdateRequest(ctx, req.(*UpdateRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// MonitoringServer_ServiceDesc is the grpc.ServiceDesc for MonitoringServer service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var MonitoringServer_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "clairvoyant.MonitoringServer",
	HandlerType: (*MonitoringServerServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "HandleUpdateRequest",
			Handler:    _MonitoringServer_HandleUpdateRequest_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "clairvoyant.proto",
}

// CVServerClient is the client API for CVServer service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type CVServerClient interface {
	HandleCVRequest(ctx context.Context, in *CVRequest, opts ...grpc.CallOption) (*CVReply, error)
}

type cVServerClient struct {
	cc grpc.ClientConnInterface
}

func NewCVServerClient(cc grpc.ClientConnInterface) CVServerClient {
	return &cVServerClient{cc}
}

func (c *cVServerClient) HandleCVRequest(ctx context.Context, in *CVRequest, opts ...grpc.CallOption) (*CVReply, error) {
	out := new(CVReply)
	err := c.cc.Invoke(ctx, "/clairvoyant.CVServer/HandleCVRequest", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// CVServerServer is the server API for CVServer service.
// All implementations must embed UnimplementedCVServerServer
// for forward compatibility
type CVServerServer interface {
	HandleCVRequest(context.Context, *CVRequest) (*CVReply, error)
	mustEmbedUnimplementedCVServerServer()
}

// UnimplementedCVServerServer must be embedded to have forward compatible implementations.
type UnimplementedCVServerServer struct {
}

func (UnimplementedCVServerServer) HandleCVRequest(context.Context, *CVRequest) (*CVReply, error) {
	return nil, status.Errorf(codes.Unimplemented, "method HandleCVRequest not implemented")
}
func (UnimplementedCVServerServer) mustEmbedUnimplementedCVServerServer() {}

// UnsafeCVServerServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to CVServerServer will
// result in compilation errors.
type UnsafeCVServerServer interface {
	mustEmbedUnimplementedCVServerServer()
}

func RegisterCVServerServer(s grpc.ServiceRegistrar, srv CVServerServer) {
	s.RegisterService(&CVServer_ServiceDesc, srv)
}

func _CVServer_HandleCVRequest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(CVRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(CVServerServer).HandleCVRequest(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/clairvoyant.CVServer/HandleCVRequest",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(CVServerServer).HandleCVRequest(ctx, req.(*CVRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// CVServer_ServiceDesc is the grpc.ServiceDesc for CVServer service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var CVServer_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "clairvoyant.CVServer",
	HandlerType: (*CVServerServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "HandleCVRequest",
			Handler:    _CVServer_HandleCVRequest_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "clairvoyant.proto",
}

// EdgeServerClient is the client API for EdgeServer service.
//
// For semantics around ctx use and closing/ending streaming RPCs, please refer to https://pkg.go.dev/google.golang.org/grpc/?tab=doc#ClientConn.NewStream.
type EdgeServerClient interface {
	HandleDownloadRequest(ctx context.Context, in *DownloadRequest, opts ...grpc.CallOption) (*DownloadReply, error)
}

type edgeServerClient struct {
	cc grpc.ClientConnInterface
}

func NewEdgeServerClient(cc grpc.ClientConnInterface) EdgeServerClient {
	return &edgeServerClient{cc}
}

func (c *edgeServerClient) HandleDownloadRequest(ctx context.Context, in *DownloadRequest, opts ...grpc.CallOption) (*DownloadReply, error) {
	out := new(DownloadReply)
	err := c.cc.Invoke(ctx, "/clairvoyant.EdgeServer/HandleDownloadRequest", in, out, opts...)
	if err != nil {
		return nil, err
	}
	return out, nil
}

// EdgeServerServer is the server API for EdgeServer service.
// All implementations must embed UnimplementedEdgeServerServer
// for forward compatibility
type EdgeServerServer interface {
	HandleDownloadRequest(context.Context, *DownloadRequest) (*DownloadReply, error)
	mustEmbedUnimplementedEdgeServerServer()
}

// UnimplementedEdgeServerServer must be embedded to have forward compatible implementations.
type UnimplementedEdgeServerServer struct {
}

func (UnimplementedEdgeServerServer) HandleDownloadRequest(context.Context, *DownloadRequest) (*DownloadReply, error) {
	return nil, status.Errorf(codes.Unimplemented, "method HandleDownloadRequest not implemented")
}
func (UnimplementedEdgeServerServer) mustEmbedUnimplementedEdgeServerServer() {}

// UnsafeEdgeServerServer may be embedded to opt out of forward compatibility for this service.
// Use of this interface is not recommended, as added methods to EdgeServerServer will
// result in compilation errors.
type UnsafeEdgeServerServer interface {
	mustEmbedUnimplementedEdgeServerServer()
}

func RegisterEdgeServerServer(s grpc.ServiceRegistrar, srv EdgeServerServer) {
	s.RegisterService(&EdgeServer_ServiceDesc, srv)
}

func _EdgeServer_HandleDownloadRequest_Handler(srv interface{}, ctx context.Context, dec func(interface{}) error, interceptor grpc.UnaryServerInterceptor) (interface{}, error) {
	in := new(DownloadRequest)
	if err := dec(in); err != nil {
		return nil, err
	}
	if interceptor == nil {
		return srv.(EdgeServerServer).HandleDownloadRequest(ctx, in)
	}
	info := &grpc.UnaryServerInfo{
		Server:     srv,
		FullMethod: "/clairvoyant.EdgeServer/HandleDownloadRequest",
	}
	handler := func(ctx context.Context, req interface{}) (interface{}, error) {
		return srv.(EdgeServerServer).HandleDownloadRequest(ctx, req.(*DownloadRequest))
	}
	return interceptor(ctx, in, info, handler)
}

// EdgeServer_ServiceDesc is the grpc.ServiceDesc for EdgeServer service.
// It's only intended for direct use with grpc.RegisterService,
// and not to be introspected or modified (even as a copy)
var EdgeServer_ServiceDesc = grpc.ServiceDesc{
	ServiceName: "clairvoyant.EdgeServer",
	HandlerType: (*EdgeServerServer)(nil),
	Methods: []grpc.MethodDesc{
		{
			MethodName: "HandleDownloadRequest",
			Handler:    _EdgeServer_HandleDownloadRequest_Handler,
		},
	},
	Streams:  []grpc.StreamDesc{},
	Metadata: "clairvoyant.proto",
}
